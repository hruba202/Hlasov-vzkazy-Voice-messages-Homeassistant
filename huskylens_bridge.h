#include "esphome.h"


#define HUSKYLENS_I2C_ADDR 0x32 // Výchozí I2C adresa HuskyLens

class HuskyLensBridge : public Component {
 private:
  unsigned long last_request_ = 0;
  i2c_port_t i2c_port_ = I2C_NUM_0;

 public:
  int id = -1;
  int x = -1;
  int y = -1;
  int width = -1;
  int height = -1;
  int command = -1;
  bool object_detected = false;

  void setup() override {
    // V ESP-IDF konfiguruje I2C sběrnici samotné ESPHome podle YAML souboru.
    // Zde pouze ověříme, zda HuskyLens na sběrnici odpovídá.
    ESP_LOGI("huskylens", "Inicializace HuskyLens na I2C sběrnici...");
  }

  void loop() override {
    unsigned long now = millis();
    if (now - last_request_ < 100) return; // Vyčítáme každých 100ms
    last_request_ = now;

    // 1. Poslat žádost o data (HuskyLens Request Command: 0x20)
    // Hlavička protokolu: 0x55 0xAA 0x11 0x00 0x20 0x30
    uint8_t req_cmd[] = {0x55, 0xAA, 0x11, 0x00, 0x20, 0x30};
    
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (HUSKYLENS_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(cmd, req_cmd, sizeof(req_cmd), true);
    i2c_master_stop(cmd);
    esp_err_t err = i2c_master_cmd_begin(i2c_port_, cmd, pdMS_TO_TICKS(10));
    i2c_cmd_link_delete(cmd);

    if (err != ESP_OK) {
      ESP_LOGD("huskylens", "I2C zápis selhal (HuskyLens neodpovídá)");
      object_detected = false;
      return;
    }

    // Krátká pauza na zpracování kamerou
    delay(5);

    // 2. Čtení odpovědi z HuskyLens (Blok dat má 16 bajtů)
    uint8_t buf[16] = {0};
    cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (HUSKYLENS_I2C_ADDR << 1) | I2C_MASTER_READ, true);
    i2c_master_read(cmd, buf, sizeof(buf), I2C_MASTER_LAST_NACK);
    i2c_master_stop(cmd);
    err = i2c_master_cmd_begin(i2c_port_, cmd, pdMS_TO_TICKS(20));
    i2c_cmd_link_delete(cmd);

    if (err != ESP_OK) {
      object_detected = false;
      return;
    }

    // 3. Validace hlavičky protokolu HuskyLens (0x55 0xAA)
    if (buf[0] == 0x55 && buf[1] == 0xAA) {
      // Protokol HuskyLens pro detekovaný objekt (Command 0x05 / IS_BLOCK)
      command = buf[4];
      
      if (command == 0x05) { 
        // Data jsou uložena v bajtech s malou endianitou (Little Endian)
        x = buf[5] | (buf[6] << 8);
        y = buf[7] | (buf[8] << 8);
        width = buf[9] | (buf[10] << 8);
        height = buf[11] | (buf[12] << 8);
        id = buf[13] | (buf[14] << 8);
        
        object_detected = true;
        ESP_LOGD("huskylens", "Objekt detekován! ID: %d, X: %d, Y: %d", id, x, y);
      } else {
        object_detected = false; // Žádný blok/objekt v záběru
      }
    } else {
      object_detected = false;
    }
  }
};

HuskyLensBridge* global_husky = new HuskyLensBridge();
