#include <U8g2lib.h>
#include <Wire.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <PubSubClient.h> 
#include <WebServer.h>
#include <ElegantOTA.h>

// ================= PENGATURAN WIFI & MQTT =================
const char* ssid = "INACOS_LABORATORY"; // change it to ur own router        
const char* password = "beingusedbyILS"; 
const char* mqtt_server = "192.168.0.101"; // this is ur ip address dekstop, check it via ipconfig on cmd
const char* topic_gateway = "TA_PTL_bee/Gateway/lapor"; //mqtt topic
const char* topic_status_umum = "TA_PTL_bee/Status"; // Buat lapor selesai

WebServer server(80);
WiFiClient espClient; 
PubSubClient mqttClient(espClient);

// ================= PENGATURAN MULTIPLEXER & OLED =================
#define TCA_ADDRESS 0x70
U8G2_SSD1306_128X32_UNIVISION_F_HW_I2C u8g2(U8G2_R0, /* reset= */ U8X8_PIN_NONE);

// ================= STRUKTUR DATA RAK =================
enum State {IDLE, ORDER, EKSEKUSI_BARANG, KONFIRMASI_AKHIR, SELESAI};

struct Rak {
  String idRak;
  String topicPerintah;
  uint8_t portMux;     // Port di Multiplexer (0 sampai 7)
  
  // Pin Hardware 
  int pinButton;
  int pinLedPutAway;
  int pinLedPicking;

  // Variabel Memori per Rak
  State statusSekarang;
  String orderType;
  String itemCode;
  String itemName;
  int reqQty;

  // Variabel Waktu & Tombol per Rak
  unsigned long t_masuk, t_ambil, t_konfirm, t_kirim, t_selesai;
  bool sudahLapor;
  bool lastButtonState;

  unsigned long uplinkStart;
  float uplinkMs;
};

// ================= ARRAY 4 RAK DALAM 1 NODE  =================
//====================== Beda rack beda struct, ganti sesuai rack=============
// ================== Jangan Lupa ganti topic nya juga =====================
//======================pinout semua sama kecuali ada yang mau di tuker=====
const int NUM_RAK = 4;
Rak racks[NUM_RAK] = {
  {"C4-1", "TA_PTL_bee/Rak_C4-1/perintah", 0, 13, 18, 14, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C4-2", "TA_PTL_bee/Rak_C4-2/perintah", 1, 27, 25, 26, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C4-4", "TA_PTL_bee/Rak_C4-4/perintah", 2, 33, 19, 32, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C4-3", "TA_PTL_bee/Rak_C4-3/perintah", 3, 23, 17, 16, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0}
};

/*  {"C2-3", "TA_PTL_bee/Rak_C2-3/perintah", 0, 13, 18, 14, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C2-1", "TA_PTL_bee/Rak_C2-1/perintah", 1, 27, 25, 26, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C2-2", "TA_PTL_bee/Rak_C2-2/perintah", 2, 33, 19, 32, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C2-4", "TA_PTL_bee/Rak_C2-4/perintah", 3, 23, 17, 16, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0}

  {"C4-1", "TA_PTL_bee/Rak_C4-1/perintah", 0, 13, 18, 14, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C4-2", "TA_PTL_bee/Rak_C4-2/perintah", 1, 27, 25, 26, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C4-4", "TA_PTL_bee/Rak_C4-4/perintah", 2, 33, 19, 32, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"C4-3", "TA_PTL_bee/Rak_C4-3/perintah", 3, 23, 17, 16, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0}

  {"B1-1", "TA_PTL_bee/Rak_B1-1/perintah", 0, 13, 18, 14, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"B1-2", "TA_PTL_bee/Rak_B1-2/perintah", 1, 27, 25, 26, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"B1-3", "TA_PTL_bee/Rak_B1-3/perintah", 2, 33, 19, 32, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"B1-4", "TA_PTL_bee/Rak_B1-4/perintah", 3, 23, 17, 16, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0}

  {"A3-3", "TA_PTL_bee/Rak_A3-3/perintah", 0, 13, 18, 14, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"A3-2", "TA_PTL_bee/Rak_A3-2/perintah", 1, 27, 25, 26, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"A3-1", "TA_PTL_bee/Rak_A3-1/perintah", 2, 33, 19, 32, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0},
  {"A3-4", "TA_PTL_bee/Rak_A3-4/perintah", 3, 23, 17, 16, IDLE, "","","", 0, 0, 0, 0, 0, 0, false, HIGH,0,0}
*/

// Variabel Global buat efek kedip (berlaku buat semua rak)
unsigned long lastBlinkTime = 0;
bool isInverse = false;
float lastUplinkMs = 0;
unsigned long upLinkStartCountdown = 0;

// ================= FUNGSI UTILITAS =================

// Cek apakah ada device I2C (OLED) di port multiplexer tert
// Fungsi Saklar I2C
void pilihLayar(uint8_t bus) {
  Wire.beginTransmission(TCA_ADDRESS);
  Wire.write(1 << bus);
  Wire.endTransmission();
}

bool cekOLED(uint8_t port) {
  pilihLayar(port);          // buka channel multiplexer ini
  delayMicroseconds(50);     // beri waktu bus settle
  Wire.beginTransmission(0x3C);   // alamat I2C OLED SSD1306
  byte error = Wire.endTransmission();
  return (error == 0);       // 0 = device menjawab (ada), selain itu = tidak ada
}

// Scan semua rak, tampilkan hasil di Serial Monitor
void cekSemuaOLED() {
  Serial.println("\n===== CEK KONEKSI OLED TIAP RAK =====");
  for (int i = 0; i < NUM_RAK; i++) {
    bool ada = cekOLED(racks[i].portMux);
    Serial.print("Rak ");
    Serial.print(racks[i].idRak);
    Serial.print(" (port ");
    Serial.print(racks[i].portMux);
    Serial.print("): ");
    Serial.println(ada ? "OK - OLED terhubung" : "GAGAL - OLED tidak terdeteksi");
  }
  Serial.println("=====================================\n");
}
// Nampilin pesan status di SEMUA OLED (saat boot/koneksi)
void showstatus(const char* pesan){
  for (int i = 0; i < NUM_RAK; i++) {
    pilihLayar(racks[i].portMux);
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_6x10_tr);
    u8g2.drawStr(0, 15, pesan);
    u8g2.sendBuffer();
  }
}

// ================= FUNGSI CALLBACK MQTT =================
void callback(char* topic, byte* payload, unsigned int length) {
  String pesan = "";
  for (int i = 0; i < length; i++) { pesan += (char)payload[i]; }
  
  String topikMasuk = String(topic);
  
  // Handle ACK Uplink untuk pengukuran latensi
if (topikMasuk == "TA_PTL_bee/ACK_Uplink") {
    JsonDocument ackDoc;
    deserializeJson(ackDoc, pesan);
    String rakAck = ackDoc["rak"].as<String>();
    for (int i = 0; i < NUM_RAK; i++) {
        if (racks[i].idRak == rakAck) {
            unsigned long now = millis();
            if (racks[i].uplinkStart > 0 && now >= racks[i].uplinkStart) {
                unsigned long dur = (now - racks[i].uplinkStart) / 2;   // round-trip → /2
                racks[i].uplinkMs = (dur > 5000) ? 0 : (float)dur;
            }
            racks[i].uplinkStart = 0;
            break;
        }
    }
    return;
}
  
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, pesan);

  if (!error) {
    // Cek ini pesanan buat rak yang mana? Loop array cari yang cocok
    Rak* rakTujuan = nullptr;
    
    for (int i = 0; i < NUM_RAK; i++) {
      if (topikMasuk == racks[i].topicPerintah && racks[i].statusSekarang == IDLE) {
        rakTujuan = &racks[i];
        break;
      }
    }

    // Kalau raknya ketemu dan lagi nganggur, masukin datanya!
    if (rakTujuan != nullptr) {
      rakTujuan->orderType = doc["order_type"].as<String>();
      rakTujuan->itemName = doc["item_name"].as<String>(); 
      rakTujuan->itemCode = doc["item_code"].as<String>(); 
      rakTujuan->reqQty = doc["req_qty"];
      
      String ackMsg = "{\"rak\":\"" + rakTujuan->idRak + "\", \"status\":\"ok\"}";
      mqttClient.publish("TA_PTL_bee/ACK_Downlink", ackMsg.c_str());

      rakTujuan->statusSekarang = ORDER;
      rakTujuan->t_masuk = millis(); 
      Serial.println("New order to rack: " + rakTujuan->idRak + " ===");
    }
  }
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Connecting to server...");
    showstatus("Connecting to server...");
    
    String clientId = "PTL_Gateway_A1" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("Connected to MQTT!");
      
      // SUBSCRIBE KE SEMUA 4 RAK
      for (int i = 0; i < NUM_RAK; i++) {
        mqttClient.subscribe(racks[i].topicPerintah.c_str());
      }
      
      // Uplink mqtt countdown
      mqttClient.subscribe("TA_PTL_bee/ACK_Uplink");
    } else {
      delay(5000);
    }
  }
}




// ================= FUNGSI LAPOR SELESAI (DINAMIS PER RAK) =================
void laporSelesai(Rak &r) {
  if (r.sudahLapor == true) return; 
  r.sudahLapor = true; 

  float dTunggu = (float)(r.t_ambil - r.t_masuk) / 1000.0;
  float dAmbil = (float)(r.t_konfirm - r.t_ambil) / 1000.0;
  float dKonfirm = (float)(r.t_kirim - r.t_konfirm) / 1000.0;
  float dTotal = (float)(r.t_kirim - r.t_masuk) / 1000.0;

  JsonDocument docLapor;
  docLapor["rack_id"] = r.idRak;
  docLapor["order_type"] = r.orderType;
  docLapor["item_name"] = r.itemName;
  docLapor["req_qty"] = r.reqQty;
  docLapor["d_tunggu"] = dTunggu;  docLapor["d_ambil"] = dAmbil;
  docLapor["d_konfirm"] = dKonfirm; docLapor["d_total"] = dTotal;

  docLapor["uplink_ms"] = r.uplinkMs;

  String pesanLapor;
  serializeJson(docLapor, pesanLapor);

  //r.uplinkStart = millis();
  mqttClient.publish(topic_gateway, pesanLapor.c_str());
  
  String statusMsg = "{\"status\": \"SELESAI\", \"rak\": \"" + r.idRak + "\"}";
  mqttClient.publish(topic_status_umum, statusMsg.c_str());
}

void nyalainOLED(String kode, int qty) {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_9x15_tf); 
  u8g2.drawStr(0, 10, kode.c_str()); // Nampilin Kode Barang (SA-001)
  
  u8g2.setFont(u8g2_font_6x10_tr); 
  u8g2.setCursor(0, 28); 
  u8g2.print("Qty: ");
  u8g2.print(qty); // Nampilin Jumlah
  
  u8g2.sendBuffer(); // Ini yang sebenernya bikin latensi paling berasa
}


// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  Wire.setClock(100000);
  Wire.setTimeOut(50);

  // Setup Pin Hardware untuk SEMUA 4 RAK
  for (int i = 0; i < NUM_RAK; i++) {
    pinMode(racks[i].pinButton, INPUT_PULLUP);
    pinMode(racks[i].pinLedPutAway, OUTPUT);
    pinMode(racks[i].pinLedPicking, OUTPUT);
  }

  // Bangunin OLED untuk SEMUA 4 RAK
 for (int i = 0; i < NUM_RAK; i++) {
    pilihLayar(racks[i].portMux);
    delay(50);
    u8g2.begin();
    u8g2.initDisplay();      // paksa init ulang di channel ini
    u8g2.setPowerSave(0);    // pastikan layar nyala
    u8g2.clearBuffer();
    u8g2.sendBuffer();
    delay(50);
}

  // >>> CEK OLED DI SINI — sebelum WiFi <
  cekSemuaOLED();
  delay(2000);   // tahan 2 detik biar sempat baca hasilnya di Serial Monitor

  // baru setelah itu konek WiFi
  Serial.print("Connecting to WiFi...");
  showstatus("Connecting to WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }

  Serial.println("\nWiFi Connected!");
  Serial.print("MY IP: ");
  Serial.println(WiFi.localIP());
  showstatus("WiFi Connected!");
  delay(1000);

  server.on("/",[](){
    server.send(200,"text/plain","OTA Connected, open /update to OTA");
  });

  ElegantOTA.begin(&server);
  server.begin();
  Serial.println("HTTP SERVER CONNECTED TO BE INVINITY AND BEYONNNNNDDD");

  mqttClient.setServer(mqtt_server, 1883);
  mqttClient.setCallback(callback);
}
// ================= MESIN PENGGERAK UTAMA PER RAK =================
// Fungsi ini ngurusin logika tombol, lampu, dan OLED untuk SATU rak
void prosesRak(Rak &r) {
  // 1. CEK TOMBOL
  bool currentButtonState = digitalRead(r.pinButton);
  if (r.lastButtonState == HIGH && currentButtonState == LOW) {
    delay(50); // Debounce
    if (r.statusSekarang == ORDER) {
      r.statusSekarang = EKSEKUSI_BARANG; r.t_ambil = millis(); 
       String tibaMsg = "{\"event\":\"arrived\",\"rak\":\"" + r.idRak + "\"}";

     r.uplinkStart = millis();
      mqttClient.publish("TA_PTL_bee/Status", tibaMsg.c_str());
    }
    else if (r.statusSekarang == EKSEKUSI_BARANG) {
      r.statusSekarang = KONFIRMASI_AKHIR; r.t_konfirm = millis(); 
    } 
    else if (r.statusSekarang == KONFIRMASI_AKHIR) {
      r.t_kirim = millis();
      laporSelesai(r);
      r.statusSekarang = SELESAI; r.t_selesai = millis(); 
    }
  }
  r.lastButtonState = currentButtonState;

  if (r.statusSekarang == SELESAI && (millis() - r.t_selesai >= 2000)) {
    r.statusSekarang = IDLE; r.sudahLapor = false; 
  }

  // 2. UPDATE LAYAR DAN LAMPU
  unsigned long startI2C = micros(); //starting stopwatch
  pilihLayar(r.portMux); // Buka pintu I2C khusus buat rak ini
  u8g2.clearBuffer();
  u8g2.setDrawColor(1); 

  if (r.statusSekarang == IDLE) {
    digitalWrite(r.pinLedPutAway, LOW); digitalWrite(r.pinLedPicking, LOW);
    u8g2.setFont(u8g2_font_helvB14_tf); 
    u8g2.drawStr(40, 24, r.idRak.c_str());
  }
  else if (r.statusSekarang == ORDER) {
    u8g2.setFont(u8g2_font_helvB14_tf);
    
    String textOrder = (r.orderType == "Picking") ? "PICKING" : "PUT-AWAY";
    
    if (r.orderType == "Picking") digitalWrite(r.pinLedPicking, HIGH);
    else digitalWrite(r.pinLedPutAway, HIGH);

    if (isInverse) {
      u8g2.drawBox(0, 0, 128, 32); u8g2.setDrawColor(0);
      u8g2.drawStr(10, 24, textOrder.c_str());
    } else {
      u8g2.drawStr(10, 24, textOrder.c_str());
    }
  }
  else if (r.statusSekarang == EKSEKUSI_BARANG) { 
    u8g2.setFont(u8g2_font_9x15_tf); 
    u8g2.drawStr(0, 10, r.itemCode.c_str()); 
    u8g2.setFont(u8g2_font_6x10_tr); u8g2.setCursor(0, 28); 
    if (r.orderType == "Picking") u8g2.print("Ambil Qty: "); else u8g2.print("Simpan Qty: ");
    u8g2.print(r.reqQty);        
  }
  else if (r.statusSekarang == KONFIRMASI_AKHIR) {
    u8g2.setFont(u8g2_font_6x10_tr); u8g2.setCursor(0, 12);
    if (r.orderType == "Picking") u8g2.print("Selesai ambil "); else u8g2.print("Selesai taruh ");
    u8g2.print(r.reqQty); u8g2.print("?");
    u8g2.drawStr(0, 28, "Pencet tombol!");
  } 
  else if (r.statusSekarang == SELESAI) {
    u8g2.setFont(u8g2_font_ncenB12_tr); u8g2.drawStr(30, 24, "DONE!");
  }
  u8g2.sendBuffer(); // Kirim gambar ke layar rak ini
  unsigned long endI2C = micros(); //stopwatch stopped

  if (r.statusSekarang == ORDER && isInverse) { 
     Serial.print("I2c Speed of " + r.idRak + ": ");
     Serial.print(endI2C - startI2C);
     Serial.println(" us");
  }
}

// ================= LOOP UTAMA =================
void loop() {
  if (WiFi.status() != WL_CONNECTED) { /* Logika Reconnect WiFi */ }
  if (!mqttClient.connected()) { reconnectMQTT(); }
  mqttClient.loop();
  server.handleClient();
  ElegantOTA.loop();

  // Pengatur kedip global
  if (millis() - lastBlinkTime >= 1000) {
    isInverse = !isInverse;
    lastBlinkTime = millis();
  }

  // JALANKAN LOGIKA UNTUK SEMUA 4 RAK SECARA PARALEL
  static unsigned long lastUpdateOLED = 0; 

  if (millis() - lastUpdateOLED >= 250) {
    for (int i = 0; i < NUM_RAK; i++) {
      prosesRak(racks[i]);
    }
    lastUpdateOLED = millis();
  }
}