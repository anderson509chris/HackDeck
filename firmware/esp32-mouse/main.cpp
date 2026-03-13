/**
 * Waveshare ESP32-S3-Touch-AMOLED-1.91 — USB HID Mouse with Menu
 *
 * Screen layout (240w x 536h, portrait):
 *   MENU MODE:  Two large buttons — "Button 1" (placeholder) and "Mouse Mode"
 *   MOUSE MODE: Full touchscreen = absolute mouse input to Windows PC
 *               Small "⬅" button in bottom-right corner — long-press 1.5s to return to menu
 *
 * Pinout (from official Waveshare schematic):
 *   Display (RM67162, QSPI):
 *     QSPI_SCK  = GPIO47   QSPI_CS   = GPIO6
 *     QSPI_D0   = GPIO18   QSPI_D1   = GPIO7
 *     QSPI_D2   = GPIO48   QSPI_D3   = GPIO5
 *     DISP_RESET= GPIO17
 *
 *   Touch (FT3168, I2C):
 *     TP_SCL = GPIO39   TP_SDA = GPIO40
 *     TP_INT = GPIO41   TP_RST = GPIO17  (shared with display reset)
 *
 * Libraries needed (add to platformio.ini lib_deps):
 *   moononournation/GFX Library for Arduino
 */

#include <Arduino.h>
#include <Wire.h>
#include <USB.h>
#include <USBHIDMouse.h>

// ── Display driver (Arduino_GFX) ─────────────────────────────────────────────
#include <Arduino_GFX_Library.h>

// QSPI bus for RM67162
Arduino_DataBus *bus = new Arduino_ESP32QSPI(
    6,   // CS
    47,  // SCK
    18,  // D0
    7,   // D1
    48,  // D2
    5    // D3
);

// RM67162 AMOLED, reset=17, landscape=false (portrait 240x536)
Arduino_GFX *gfx = new Arduino_RM67162(bus, 17 /*RST*/, 0 /*rotation: portrait*/);

// ── Touch (FT3168 via I2C) ────────────────────────────────────────────────────
#define TP_SDA      40
#define TP_SCL      39
#define TP_INT      41
#define TP_RST      17   // shared with display reset — already handled by GFX init

#define FT3168_ADDR 0x38

// ── Display dimensions ────────────────────────────────────────────────────────
#define SCREEN_W    240
#define SCREEN_H    536

// ── USB HID Mouse ─────────────────────────────────────────────────────────────
USBHIDMouse Mouse;
#define MOUSE_MAX   32767   // HID absolute mouse range

// ── App state ─────────────────────────────────────────────────────────────────
enum AppState { STATE_MENU, STATE_MOUSE };
AppState appState = STATE_MENU;

// ── Colors ────────────────────────────────────────────────────────────────────
#define COL_BG          0x1082   // very dark grey
#define COL_BTN1        0x2945   // dark blue-grey  (placeholder button)
#define COL_BTN2        0x0540   // dark green      (mouse button)
#define COL_BTN_PRESS   0x4228   // lighter press flash
#define COL_TEXT        0xFFFF   // white
#define COL_BACK_BTN    0x8410   // medium grey back button
#define COL_BACK_PRESS  0xC618   // light grey press flash
#define COL_OVERLAY     0x2104   // semi-dark overlay strip at bottom

// ── Button geometry (menu) ────────────────────────────────────────────────────
#define MENU_BTN_X      20
#define MENU_BTN_W      200
#define MENU_BTN_H      90
#define MENU_BTN1_Y     160
#define MENU_BTN2_Y     290
#define MENU_BTN_R      14       // corner radius

// ── Back button geometry (mouse mode, bottom-right) ───────────────────────────
#define BACK_BTN_W      52
#define BACK_BTN_H      36
#define BACK_BTN_X      (SCREEN_W - BACK_BTN_W - 6)
#define BACK_BTN_Y      (SCREEN_H - BACK_BTN_H - 6)
#define BACK_HOLD_MS    1500     // long-press duration to go back

// ── Touch state ───────────────────────────────────────────────────────────────
struct Touch {
    bool     active;
    uint16_t x, y;
};

Touch lastTouch = {false, 0, 0};

// Long-press tracking for back button
bool     backBtnHeld    = false;
uint32_t backBtnHoldStart = 0;
bool     backBtnTriggered = false;

// ── Forward declarations ──────────────────────────────────────────────────────
void     drawMenu();
void     drawMouseScreen();
void     drawBackBtn(bool pressed);
Touch    readTouch();
bool     inRect(uint16_t tx, uint16_t ty, int x, int y, int w, int h);
void     enterMouseMode();
void     enterMenuMode();

// ─────────────────────────────────────────────────────────────────────────────
//  Touch reading — FT3168 over I2C
// ─────────────────────────────────────────────────────────────────────────────
Touch readTouch() {
    Touch t = {false, 0, 0};

    Wire.beginTransmission(FT3168_ADDR);
    Wire.write(0x02);  // TD_STATUS register (number of touch points)
    if (Wire.endTransmission(false) != 0) return t;

    Wire.requestFrom((uint8_t)FT3168_ADDR, (uint8_t)7);
    if (Wire.available() < 7) return t;

    uint8_t tdStatus = Wire.read();   // number of touch points
    uint8_t xh       = Wire.read();
    uint8_t xl       = Wire.read();
    uint8_t yh       = Wire.read();
    uint8_t yl       = Wire.read();
    Wire.read();  // weight
    Wire.read();  // misc

    if ((tdStatus & 0x0F) == 0) return t;

    t.active = true;
    t.x = ((xh & 0x0F) << 8) | xl;
    t.y = ((yh & 0x0F) << 8) | yl;
    return t;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Hit-test helper
// ─────────────────────────────────────────────────────────────────────────────
bool inRect(uint16_t tx, uint16_t ty, int x, int y, int w, int h) {
    return (tx >= x && tx <= x + w && ty >= y && ty <= y + h);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Draw helpers
// ─────────────────────────────────────────────────────────────────────────────
void drawRoundRect(int x, int y, int w, int h, int r, uint16_t color) {
    gfx->fillRoundRect(x, y, w, h, r, color);
}

void drawMenu() {
    gfx->fillScreen(COL_BG);

    // Title
    gfx->setTextColor(COL_TEXT);
    gfx->setTextSize(2);
    gfx->setCursor(60, 60);
    gfx->print("Main Menu");

    // Button 1 — placeholder
    drawRoundRect(MENU_BTN_X, MENU_BTN1_Y, MENU_BTN_W, MENU_BTN_H, MENU_BTN_R, COL_BTN1);
    gfx->setTextColor(COL_TEXT);
    gfx->setTextSize(2);
    gfx->setCursor(MENU_BTN_X + 40, MENU_BTN1_Y + 32);
    gfx->print("Button 1");

    // Button 2 — Mouse Mode
    drawRoundRect(MENU_BTN_X, MENU_BTN2_Y, MENU_BTN_W, MENU_BTN_H, MENU_BTN_R, COL_BTN2);
    gfx->setTextColor(COL_TEXT);
    gfx->setTextSize(2);
    gfx->setCursor(MENU_BTN_X + 28, MENU_BTN2_Y + 32);
    gfx->print("Mouse Mode");
}

void drawBackBtn(bool pressed) {
    uint16_t col = pressed ? COL_BACK_PRESS : COL_BACK_BTN;
    drawRoundRect(BACK_BTN_X, BACK_BTN_Y, BACK_BTN_W, BACK_BTN_H, 8, col);
    gfx->setTextColor(COL_TEXT);
    gfx->setTextSize(1);
    gfx->setCursor(BACK_BTN_X + 8, BACK_BTN_Y + 12);
    gfx->print("MENU");
}

void drawMouseScreen() {
    gfx->fillScreen(0x0000);  // black — touch anywhere = mouse

    // Subtle label at top so user knows what mode they're in
    gfx->setTextColor(0x4228);
    gfx->setTextSize(1);
    gfx->setCursor(6, 6);
    gfx->print("Touch = Mouse  |  Hold MENU to exit");

    drawBackBtn(false);
}

// ─────────────────────────────────────────────────────────────────────────────
//  State transitions
// ─────────────────────────────────────────────────────────────────────────────
void enterMouseMode() {
    appState = STATE_MOUSE;
    backBtnHeld      = false;
    backBtnTriggered = false;
    drawMouseScreen();
}

void enterMenuMode() {
    appState = STATE_MENU;
    Mouse.release(MOUSE_LEFT);  // make sure no phantom clicks
    drawMenu();
}

// ─────────────────────────────────────────────────────────────────────────────
//  setup()
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
    // USB HID — must be called before USB.begin()
    Mouse.begin();
    USB.begin();

    // Display
    gfx->begin();
    gfx->fillScreen(COL_BG);

    // Touch I2C
    Wire.begin(TP_SDA, TP_SCL, 400000UL);
    pinMode(TP_INT, INPUT_PULLUP);

    // Short delay for everything to settle
    delay(200);

    drawMenu();
}

// ─────────────────────────────────────────────────────────────────────────────
//  loop()
// ─────────────────────────────────────────────────────────────────────────────
void loop() {
    Touch t = readTouch();

    // ── MENU MODE ─────────────────────────────────────────────────────────────
    if (appState == STATE_MENU) {
        if (t.active) {
            // Button 1 — placeholder, flash colour only for now
            if (inRect(t.x, t.y, MENU_BTN_X, MENU_BTN1_Y, MENU_BTN_W, MENU_BTN_H)) {
                drawRoundRect(MENU_BTN_X, MENU_BTN1_Y, MENU_BTN_W, MENU_BTN_H,
                              MENU_BTN_R, COL_BTN_PRESS);
                delay(120);
                drawRoundRect(MENU_BTN_X, MENU_BTN1_Y, MENU_BTN_W, MENU_BTN_H,
                              MENU_BTN_R, COL_BTN1);
                // TODO: add Button 1 functionality here
            }

            // Button 2 — enter Mouse Mode
            if (inRect(t.x, t.y, MENU_BTN_X, MENU_BTN2_Y, MENU_BTN_W, MENU_BTN_H)) {
                drawRoundRect(MENU_BTN_X, MENU_BTN2_Y, MENU_BTN_W, MENU_BTN_H,
                              MENU_BTN_R, COL_BTN_PRESS);
                delay(120);
                enterMouseMode();
            }
        }
        delay(30);
        return;
    }

    // ── MOUSE MODE ────────────────────────────────────────────────────────────
    if (appState == STATE_MOUSE) {

        bool overBackBtn = t.active &&
                           inRect(t.x, t.y, BACK_BTN_X, BACK_BTN_Y, BACK_BTN_W, BACK_BTN_H);

        // ── Back button long-press logic ──────────────────────────────────────
        if (overBackBtn) {
            if (!backBtnHeld) {
                // Finger just landed on back button
                backBtnHeld      = true;
                backBtnTriggered = false;
                backBtnHoldStart = millis();
                drawBackBtn(true);   // visual press feedback
                Mouse.release(MOUSE_LEFT);
            } else if (!backBtnTriggered) {
                // Check if held long enough
                if (millis() - backBtnHoldStart >= BACK_HOLD_MS) {
                    backBtnTriggered = true;
                    enterMenuMode();
                    return;
                }
            }
            // While holding back button, don't send mouse events
            delay(10);
            return;
        } else {
            // Finger left back button area
            if (backBtnHeld) {
                backBtnHeld = false;
                drawBackBtn(false);  // reset visual
            }
        }

        // ── Normal touch → mouse movement ─────────────────────────────────────
        if (t.active) {
            // Map touch coords to absolute HID mouse range 0–32767
            int16_t mx = (int16_t)map(t.x, 0, SCREEN_W - 1, 0, MOUSE_MAX);
            int16_t my = (int16_t)map(t.y, 0, SCREEN_H - 1, 0, MOUSE_MAX);

            Mouse.move(mx, my, 0, 0);  // absolute move

            if (!lastTouch.active) {
                Mouse.press(MOUSE_LEFT);   // finger down → click
            }
        } else {
            if (lastTouch.active) {
                Mouse.release(MOUSE_LEFT); // finger up → release
            }
        }

        lastTouch = t;
        delay(10);
    }
}
