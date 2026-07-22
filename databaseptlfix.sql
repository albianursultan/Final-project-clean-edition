kabinet-- ============================================================
--  PTL DATABASE - CLEAN SCRIPT
--  Drop & recreate from scratch
-- ============================================================

DROP DATABASE IF EXISTS ptl_database;
CREATE DATABASE ptl_database;
USE ptl_database;

-- ------------------------------------------------------------
--  TABLE DEFINITIONS
-- ------------------------------------------------------------

CREATE TABLE rack (
    rack_id VARCHAR(10) PRIMARY KEY,
    aisle CHAR(1) NOT NULL,
    column_number INT NOT NULL
);

CREATE TABLE item (
    item_code VARCHAR(10) PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL
);

CREATE TABLE kabinet (
    kabinet_id VARCHAR(10) PRIMARY KEY,
    rack_id VARCHAR(10) NOT NULL,
    item_code VARCHAR(10) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    FOREIGN KEY (rack_id) REFERENCES rack(rack_id),
    FOREIGN KEY (item_code) REFERENCES item(item_code)
);

-- ------------------------------------------------------------
--  RACK
-- ------------------------------------------------------------

INSERT INTO rack (rack_id, aisle, column_number) VALUES
('A1', 'A', 1),
('A2', 'A', 2),
('A3', 'A', 3),
('A4', 'A', 4),
('B1', 'B', 1),
('B2', 'B', 2),
('B3', 'B', 3),
('B4', 'B', 4),
('C1', 'C', 1),
('C2', 'C', 2),
('C3', 'C', 3),
('C4', 'C', 4);

-- ------------------------------------------------------------
--  ITEM
-- ------------------------------------------------------------

INSERT INTO item (item_code, item_name, category) VALUES
-- Sensor & Actuator
('SA-001', 'Sensor Ultrasonik HC-SR04', 'Sensor & Actuator'),
('SA-002', 'Sensor IR Obstacle',        'Sensor & Actuator'),
('SA-003', 'Encoder Rotary',            'Sensor & Actuator'),
('SA-004', 'Servo Motor SG90',          'Sensor & Actuator'),
('SA-005', 'Sensor Suhu DHT11',         'Sensor & Actuator'),
('SA-006', 'Modul RTC DS3231',          'Sensor & Actuator'),
('SA-007', 'Relay 5V 1 Channel',        'Sensor & Actuator'),
('SA-008', 'Modul MPU6050',             'Sensor & Actuator'),
('SA-009', 'Modul RFID RC522',          'Sensor & Actuator'),
('SA-010', 'Joystick Module',           'Sensor & Actuator'),
('SA-011', 'LCD I2C 16x2',              'Sensor & Actuator'),
('SA-012', 'Sensor LDR Cahaya',         'Sensor & Actuator'),
('SA-013', 'Modul Bluetooth HC05',      'Sensor & Actuator'),
('SA-014', 'Sensor Warna TCS3200',      'Sensor & Actuator'),
('SA-015', 'Sensor Gas MQ-2',           'Sensor & Actuator'),
('SA-016', 'Modul Load Cell',           'Sensor & Actuator'),
-- Mechanic & Part
('MK-001', 'Bearing 608ZZ',             'Mechanic & Part'),
('MK-002', 'Pulley GT2 20T',            'Mechanic & Part'),
('MK-003', 'Linear Rail 300mm',         'Mechanic & Part'),
('MK-004', 'Timing Belt GT2',           'Mechanic & Part'),
('MK-005', 'Baut M3 x 10mm',           'Mechanic & Part'),
('MK-006', 'Mur M3 Stainless',         'Mechanic & Part'),
('MK-007', 'Spacer Kuningan M3',        'Mechanic & Part'),
('MK-008', 'Alum. Profile 2020',        'Mechanic & Part'),
('MK-009', 'Roda Omni 58mm',            'Mechanic & Part'),
('MK-010', 'Besi Shaft 8mm',            'Mechanic & Part'),
('MK-011', 'Coupler 5x8mm',             'Mechanic & Part'),
('MK-012', 'Gear Plastik Set',          'Mechanic & Part'),
('MK-013', 'V-Wheel Pom',               'Mechanic & Part'),
('MK-014', 'Lead Screw T8',             'Mechanic & Part'),
('MK-015', 'Motor Stepper Nema17',      'Mechanic & Part'),
('MK-016', 'Bracket Nema 17',           'Mechanic & Part'),
-- Electronic Component
('EL-001', 'Resistor 10K Ohm',          'Electronic Component'),
('EL-002', 'Kapasitor 100uF',           'Electronic Component'),
('EL-003', 'LED Merah 5mm',             'Electronic Component'),
('EL-004', 'Transistor 2N2222',         'Electronic Component'),
('EL-005', 'ESP32 Dev Module',          'Electronic Component'),
('EL-006', 'Arduino Uno R3',            'Electronic Component'),
('EL-007', 'Raspberry Pi 4',            'Electronic Component'),
('EL-008', 'Breadboard 400 Hole',       'Electronic Component'),
('EL-009', 'Kabel Jumper M-M',          'Electronic Component'),
('EL-010', 'Baterai 18650',             'Electronic Component'),
('EL-011', 'Modul BMS 3S',              'Electronic Component'),
('EL-012', 'Step Down LM2596',          'Electronic Component'),
('EL-013', 'Dioda IN4007',              'Electronic Component'),
('EL-014', 'IC 555 Timer',              'Electronic Component'),
('EL-015', 'Push Button 12mm',          'Electronic Component'),
('EL-016', 'Buzzer Aktif 5V',           'Electronic Component');

-- ------------------------------------------------------------
--  KABINET
-- ------------------------------------------------------------

INSERT INTO kabinet (kabinet_id, rack_id, item_code, quantity) VALUES
-- Aisle A - Sensor & Actuator
('A1-1', 'A1', 'SA-001', 50),
('A1-2', 'A1', 'SA-002', 50),
('A1-3', 'A1', 'SA-003', 50),
('A1-4', 'A1', 'SA-004', 50),
('A2-1', 'A2', 'SA-005', 50),
('A2-2', 'A2', 'SA-006', 50),
('A2-3', 'A2', 'SA-007', 50),
('A2-4', 'A2', 'SA-008', 50),
('A3-1', 'A3', 'SA-009', 50),
('A3-2', 'A3', 'SA-010', 50),
('A3-3', 'A3', 'SA-011', 50),
('A3-4', 'A3', 'SA-012', 50),
('A4-1', 'A4', 'SA-013', 50),
('A4-2', 'A4', 'SA-014', 50),
('A4-3', 'A4', 'SA-015', 50),
('A4-4', 'A4', 'SA-016', 50),
-- Aisle B - Mechanic & Part
('B1-1', 'B1', 'MK-001', 50),
('B1-2', 'B1', 'MK-002', 50),
('B1-3', 'B1', 'MK-003', 50),
('B1-4', 'B1', 'MK-004', 50),
('B2-1', 'B2', 'MK-005', 50),
('B2-2', 'B2', 'MK-006', 50),
('B2-3', 'B2', 'MK-007', 50),
('B2-4', 'B2', 'MK-008', 50),
('B3-1', 'B3', 'MK-009', 50),
('B3-2', 'B3', 'MK-010', 50),
('B3-3', 'B3', 'MK-011', 50),
('B3-4', 'B3', 'MK-012', 50),
('B4-1', 'B4', 'MK-013', 50),
('B4-2', 'B4', 'MK-014', 50),
('B4-3', 'B4', 'MK-015', 50),
('B4-4', 'B4', 'MK-016', 50),
-- Aisle C - Electronic Component
('C1-1', 'C1', 'EL-001', 50),
('C1-2', 'C1', 'EL-002', 50),
('C1-3', 'C1', 'EL-003', 50),
('C1-4', 'C1', 'EL-004', 50),
('C2-1', 'C2', 'EL-005', 50),
('C2-2', 'C2', 'EL-006', 50),
('C2-3', 'C2', 'EL-007', 50),
('C2-4', 'C2', 'EL-008', 50),
('C3-1', 'C3', 'EL-009', 50),
('C3-2', 'C3', 'EL-010', 50),
('C3-3', 'C3', 'EL-011', 50),
('C3-4', 'C3', 'EL-012', 50),
('C4-1', 'C4', 'EL-013', 50),
('C4-2', 'C4', 'EL-014', 50),
('C4-3', 'C4', 'EL-015', 50),
('C4-4', 'C4', 'EL-016', 50);