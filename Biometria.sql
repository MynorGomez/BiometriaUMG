-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: sistema_biometrico_umg
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `accesos_biometricos`
--

DROP TABLE IF EXISTS `accesos_biometricos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accesos_biometricos` (
  `id_acceso` int NOT NULL AUTO_INCREMENT,
  `id_persona` int DEFAULT NULL,
  `tipo_acceso` enum('entrada_principal','salon') COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_salon` int DEFAULT NULL,
  `fecha_hora` datetime DEFAULT CURRENT_TIMESTAMP,
  `similitud` decimal(5,2) DEFAULT NULL,
  `resultado` enum('aceptado','rechazado') COLLATE utf8mb4_unicode_ci DEFAULT 'aceptado',
  PRIMARY KEY (`id_acceso`),
  KEY `id_persona` (`id_persona`),
  KEY `id_salon` (`id_salon`),
  KEY `idx_acceso_fecha` (`fecha_hora`),
  CONSTRAINT `accesos_biometricos_ibfk_1` FOREIGN KEY (`id_persona`) REFERENCES `personas` (`id_persona`) ON DELETE SET NULL,
  CONSTRAINT `accesos_biometricos_ibfk_2` FOREIGN KEY (`id_salon`) REFERENCES `salones` (`id_salon`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accesos_biometricos`
--

LOCK TABLES `accesos_biometricos` WRITE;
/*!40000 ALTER TABLE `accesos_biometricos` DISABLE KEYS */;
/*!40000 ALTER TABLE `accesos_biometricos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `asignacion_cursos`
--

DROP TABLE IF EXISTS `asignacion_cursos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `asignacion_cursos` (
  `id_asignacion` int NOT NULL AUTO_INCREMENT,
  `id_curso` int NOT NULL,
  `id_rol_persona` int NOT NULL,
  `id_seccion` int NOT NULL,
  `ciclo` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `anio` year DEFAULT NULL,
  `id_salon` int DEFAULT NULL,
  `id_jornada` int DEFAULT NULL,
  PRIMARY KEY (`id_asignacion`),
  KEY `id_curso` (`id_curso`),
  KEY `id_rol_persona` (`id_rol_persona`),
  KEY `id_seccion` (`id_seccion`),
  KEY `id_salon` (`id_salon`),
  KEY `id_jornada` (`id_jornada`),
  CONSTRAINT `asignacion_cursos_ibfk_1` FOREIGN KEY (`id_curso`) REFERENCES `cursos` (`id_curso`) ON DELETE CASCADE,
  CONSTRAINT `asignacion_cursos_ibfk_2` FOREIGN KEY (`id_rol_persona`) REFERENCES `roles_persona` (`id_rol_persona`) ON DELETE CASCADE,
  CONSTRAINT `asignacion_cursos_ibfk_3` FOREIGN KEY (`id_seccion`) REFERENCES `secciones` (`id_seccion`) ON DELETE CASCADE,
  CONSTRAINT `fk_asignacion_jornada` FOREIGN KEY (`id_jornada`) REFERENCES `jornadas` (`id_jornada`),
  CONSTRAINT `fk_asignacion_salon` FOREIGN KEY (`id_salon`) REFERENCES `salones` (`id_salon`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `asignacion_cursos`
--

LOCK TABLES `asignacion_cursos` WRITE;
/*!40000 ALTER TABLE `asignacion_cursos` DISABLE KEYS */;
/*!40000 ALTER TABLE `asignacion_cursos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `asistencias`
--

DROP TABLE IF EXISTS `asistencias`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `asistencias` (
  `id_asistencia` int NOT NULL AUTO_INCREMENT,
  `id_inscripcion` int NOT NULL,
  `fecha` date NOT NULL,
  `hora_entrada` time DEFAULT NULL,
  `estado` enum('presente','ausente','tarde') COLLATE utf8mb4_unicode_ci DEFAULT 'presente',
  `metodo_registro` enum('facial','manual') COLLATE utf8mb4_unicode_ci DEFAULT 'facial',
  `confirmada_docente` tinyint(1) DEFAULT '0',
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id_asistencia`),
  KEY `id_inscripcion` (`id_inscripcion`),
  KEY `idx_asistencia_fecha` (`fecha`),
  CONSTRAINT `asistencias_ibfk_1` FOREIGN KEY (`id_inscripcion`) REFERENCES `inscripciones` (`id_inscripcion`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `asistencias`
--

LOCK TABLES `asistencias` WRITE;
/*!40000 ALTER TABLE `asistencias` DISABLE KEYS */;
/*!40000 ALTER TABLE `asistencias` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `camaras`
--

DROP TABLE IF EXISTS `camaras`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `camaras` (
  `cam_id` varchar(50) NOT NULL,
  `nombre` varchar(120) DEFAULT NULL,
  `source` varchar(255) DEFAULT NULL,
  `id_sede` int DEFAULT NULL,
  `descripcion` text,
  PRIMARY KEY (`cam_id`),
  KEY `fk_camaras_sedes` (`id_sede`),
  CONSTRAINT `fk_camaras_sedes` FOREIGN KEY (`id_sede`) REFERENCES `sedes` (`id_sede`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `camaras`
--

LOCK TABLES `camaras` WRITE;
/*!40000 ALTER TABLE `camaras` DISABLE KEYS */;
INSERT INTO `camaras` VALUES ('cam1','Puerta Principal','http://10.159.145.12:4747/video',1,'Camara puerta principal'),('cam2','Salon 306','http://192.168.1.72:4747/video',1,'IPCam salon 306');
/*!40000 ALTER TABLE `camaras` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `camera_mappings`
--

DROP TABLE IF EXISTS `camera_mappings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `camera_mappings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cam_id` varchar(50) NOT NULL,
  `id_salon` int DEFAULT NULL,
  `id_sede_carrera` int DEFAULT NULL,
  `id_jornada` int DEFAULT NULL,
  `activo` tinyint(1) DEFAULT '1',
  `id_seccion` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ux_cammap` (`cam_id`,`id_salon`,`id_sede_carrera`,`id_jornada`),
  KEY `cam_id` (`cam_id`),
  KEY `id_salon` (`id_salon`),
  KEY `id_sede_carrera` (`id_sede_carrera`),
  KEY `id_jornada` (`id_jornada`),
  KEY `id_seccion` (`id_seccion`),
  CONSTRAINT `fk_cammap_cam` FOREIGN KEY (`cam_id`) REFERENCES `camaras` (`cam_id`),
  CONSTRAINT `fk_cammap_jornada` FOREIGN KEY (`id_jornada`) REFERENCES `jornadas` (`id_jornada`),
  CONSTRAINT `fk_cammap_salon` FOREIGN KEY (`id_salon`) REFERENCES `salones` (`id_salon`),
  CONSTRAINT `fk_cammap_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `secciones` (`id_seccion`),
  CONSTRAINT `fk_cammap_sede_carrera` FOREIGN KEY (`id_sede_carrera`) REFERENCES `sede_carrera` (`id_sede_carrera`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `camera_mappings`
--

LOCK TABLES `camera_mappings` WRITE;
/*!40000 ALTER TABLE `camera_mappings` DISABLE KEYS */;
/*!40000 ALTER TABLE `camera_mappings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `carnets`
--

DROP TABLE IF EXISTS `carnets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `carnets` (
  `id_carnet` int NOT NULL AUTO_INCREMENT,
  `id_persona` int NOT NULL,
  `codigo_qr` text COLLATE utf8mb4_unicode_ci,
  `pdf_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_generacion` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_carnet`),
  KEY `id_persona` (`id_persona`),
  CONSTRAINT `carnets_ibfk_1` FOREIGN KEY (`id_persona`) REFERENCES `personas` (`id_persona`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `carnets`
--

LOCK TABLES `carnets` WRITE;
/*!40000 ALTER TABLE `carnets` DISABLE KEYS */;
/*!40000 ALTER TABLE `carnets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `carreras`
--

DROP TABLE IF EXISTS `carreras`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `carreras` (
  `id_carrera` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id_carrera`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `carreras`
--

LOCK TABLES `carreras` WRITE;
/*!40000 ALTER TABLE `carreras` DISABLE KEYS */;
INSERT INTO `carreras` VALUES (1,'Ingeniería en Sistemas',NULL),(2,'Derecho',NULL),(3,'Medicina',NULL);
/*!40000 ALTER TABLE `carreras` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cursos`
--

DROP TABLE IF EXISTS `cursos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cursos` (
  `id_curso` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `codigo` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creditos` int DEFAULT '0',
  `id_sede_carrera` int DEFAULT NULL,
  PRIMARY KEY (`id_curso`),
  UNIQUE KEY `codigo` (`codigo`),
  KEY `id_sede_carrera` (`id_sede_carrera`),
  KEY `idx_curso_codigo` (`codigo`),
  CONSTRAINT `cursos_ibfk_1` FOREIGN KEY (`id_sede_carrera`) REFERENCES `sede_carrera` (`id_sede_carrera`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cursos`
--

LOCK TABLES `cursos` WRITE;
/*!40000 ALTER TABLE `cursos` DISABLE KEYS */;
INSERT INTO `cursos` VALUES (5,'Programación I','SIS101',5,1),(6,'Base de Datos I','SIS102',4,1),(7,'Física I','SIS103',5,1),(8,'Derecho Penal','DER101',4,2);
/*!40000 ALTER TABLE `cursos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `horarios`
--

DROP TABLE IF EXISTS `horarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `horarios` (
  `id_horario` int NOT NULL AUTO_INCREMENT,
  `id_asignacion` int NOT NULL,
  `id_salon` int NOT NULL,
  `id_jornada` int NOT NULL,
  `dia_semana` enum('lunes','martes','miercoles','jueves','viernes','sabado') COLLATE utf8mb4_unicode_ci NOT NULL,
  `hora_inicio` time NOT NULL,
  `hora_fin` time NOT NULL,
  PRIMARY KEY (`id_horario`),
  KEY `id_asignacion` (`id_asignacion`),
  KEY `id_salon` (`id_salon`),
  KEY `id_jornada` (`id_jornada`),
  KEY `idx_horario_dia` (`dia_semana`),
  CONSTRAINT `horarios_ibfk_1` FOREIGN KEY (`id_asignacion`) REFERENCES `asignacion_cursos` (`id_asignacion`) ON DELETE CASCADE,
  CONSTRAINT `horarios_ibfk_2` FOREIGN KEY (`id_salon`) REFERENCES `salones` (`id_salon`) ON DELETE CASCADE,
  CONSTRAINT `horarios_ibfk_3` FOREIGN KEY (`id_jornada`) REFERENCES `jornadas` (`id_jornada`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `horarios`
--

LOCK TABLES `horarios` WRITE;
/*!40000 ALTER TABLE `horarios` DISABLE KEYS */;
/*!40000 ALTER TABLE `horarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `inscripciones`
--

DROP TABLE IF EXISTS `inscripciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inscripciones` (
  `id_inscripcion` int NOT NULL AUTO_INCREMENT,
  `id_rol_persona` int NOT NULL,
  `id_asignacion` int NOT NULL,
  `fecha_inscripcion` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_inscripcion`),
  KEY `id_rol_persona` (`id_rol_persona`),
  KEY `id_asignacion` (`id_asignacion`),
  CONSTRAINT `inscripciones_ibfk_1` FOREIGN KEY (`id_rol_persona`) REFERENCES `roles_persona` (`id_rol_persona`) ON DELETE CASCADE,
  CONSTRAINT `inscripciones_ibfk_2` FOREIGN KEY (`id_asignacion`) REFERENCES `asignacion_cursos` (`id_asignacion`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `inscripciones`
--

LOCK TABLES `inscripciones` WRITE;
/*!40000 ALTER TABLE `inscripciones` DISABLE KEYS */;
/*!40000 ALTER TABLE `inscripciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jornadas`
--

DROP TABLE IF EXISTS `jornadas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `jornadas` (
  `id_jornada` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_jornada`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jornadas`
--

LOCK TABLES `jornadas` WRITE;
/*!40000 ALTER TABLE `jornadas` DISABLE KEYS */;
INSERT INTO `jornadas` VALUES (1,'Matutina',NULL),(2,'Vespertina',NULL),(3,'Nocturna',NULL),(4,'Sabado',NULL),(36,'Domingo',NULL);
/*!40000 ALTER TABLE `jornadas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jornadas_sedes`
--

DROP TABLE IF EXISTS `jornadas_sedes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `jornadas_sedes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_jornada` int NOT NULL,
  `id_sede` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ux_jornada_sede` (`id_jornada`,`id_sede`),
  KEY `id_jornada` (`id_jornada`),
  KEY `id_sede` (`id_sede`),
  CONSTRAINT `fk_jornadasedes_jornada` FOREIGN KEY (`id_jornada`) REFERENCES `jornadas` (`id_jornada`),
  CONSTRAINT `fk_jornadasedes_sede` FOREIGN KEY (`id_sede`) REFERENCES `sedes` (`id_sede`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jornadas_sedes`
--

LOCK TABLES `jornadas_sedes` WRITE;
/*!40000 ALTER TABLE `jornadas_sedes` DISABLE KEYS */;
/*!40000 ALTER TABLE `jornadas_sedes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `personas`
--

DROP TABLE IF EXISTS `personas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `personas` (
  `id_persona` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `apellido` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dpi` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carnet` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefono` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo_personal` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo_institucional` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `foto` longblob,
  `firma` longblob,
  `encoding_facial` longtext COLLATE utf8mb4_unicode_ci,
  `estado` enum('activo','inactivo','restringido') COLLATE utf8mb4_unicode_ci DEFAULT 'activo',
  `fecha_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_persona`),
  UNIQUE KEY `dpi` (`dpi`),
  UNIQUE KEY `carnet` (`carnet`),
  UNIQUE KEY `correo_institucional` (`correo_institucional`),
  KEY `idx_persona_correo` (`correo_institucional`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `personas`
--

LOCK TABLES `personas` WRITE;
/*!40000 ALTER TABLE `personas` DISABLE KEYS */;
INSERT INTO `personas` VALUES (2,'Admin','Nombre',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'activo','2026-05-27 04:27:21'),(3,'Admin','Nombre',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'activo','2026-05-27 04:34:23'),(4,'Admin','Nombre',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'activo','2026-05-27 04:35:28');
/*!40000 ALTER TABLE `personas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `reconocimiento_logs`
--

DROP TABLE IF EXISTS `reconocimiento_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reconocimiento_logs` (
  `id_log` int NOT NULL AUTO_INCREMENT,
  `id_persona` int DEFAULT NULL,
  `similitud` decimal(5,2) DEFAULT NULL,
  `resultado` enum('reconocido','no_reconocido') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imagen_capturada` longtext COLLATE utf8mb4_unicode_ci,
  `fecha` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_log`),
  KEY `id_persona` (`id_persona`),
  CONSTRAINT `reconocimiento_logs_ibfk_1` FOREIGN KEY (`id_persona`) REFERENCES `personas` (`id_persona`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reconocimiento_logs`
--

LOCK TABLES `reconocimiento_logs` WRITE;
/*!40000 ALTER TABLE `reconocimiento_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `reconocimiento_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `reportes`
--

DROP TABLE IF EXISTS `reportes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reportes` (
  `id_reporte` int NOT NULL AUTO_INCREMENT,
  `id_asignacion` int DEFAULT NULL,
  `fecha_generacion` datetime DEFAULT CURRENT_TIMESTAMP,
  `pdf_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_reporte`),
  KEY `id_asignacion` (`id_asignacion`),
  CONSTRAINT `reportes_ibfk_1` FOREIGN KEY (`id_asignacion`) REFERENCES `asignacion_cursos` (`id_asignacion`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reportes`
--

LOCK TABLES `reportes` WRITE;
/*!40000 ALTER TABLE `reportes` DISABLE KEYS */;
/*!40000 ALTER TABLE `reportes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `id_rol` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id_rol`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles`
--

LOCK TABLES `roles` WRITE;
/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
INSERT INTO `roles` VALUES (1,'administrativo'),(2,'catedratico'),(5,'coordinador'),(3,'estudiante'),(4,'seguridad');
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles_persona`
--

DROP TABLE IF EXISTS `roles_persona`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles_persona` (
  `id_rol_persona` int NOT NULL AUTO_INCREMENT,
  `id_persona` int NOT NULL,
  `id_rol` int NOT NULL,
  `id_jornada` int DEFAULT NULL,
  PRIMARY KEY (`id_rol_persona`),
  KEY `id_persona` (`id_persona`),
  KEY `id_rol` (`id_rol`),
  KEY `id_jornada` (`id_jornada`),
  CONSTRAINT `fk_rolespersona_jornada` FOREIGN KEY (`id_jornada`) REFERENCES `jornadas` (`id_jornada`),
  CONSTRAINT `roles_persona_ibfk_1` FOREIGN KEY (`id_persona`) REFERENCES `personas` (`id_persona`) ON DELETE CASCADE,
  CONSTRAINT `roles_persona_ibfk_2` FOREIGN KEY (`id_rol`) REFERENCES `roles` (`id_rol`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles_persona`
--

LOCK TABLES `roles_persona` WRITE;
/*!40000 ALTER TABLE `roles_persona` DISABLE KEYS */;
INSERT INTO `roles_persona` VALUES (1,2,1,NULL),(2,3,1,NULL),(3,4,1,NULL);
/*!40000 ALTER TABLE `roles_persona` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `salones`
--

DROP TABLE IF EXISTS `salones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `salones` (
  `id_salon` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `capacidad` int DEFAULT '40',
  `id_sede` int NOT NULL,
  `codigo` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ubicacion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `descripcion` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id_salon`),
  KEY `id_sede` (`id_sede`),
  CONSTRAINT `salones_ibfk_1` FOREIGN KEY (`id_sede`) REFERENCES `sedes` (`id_sede`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `salones`
--

LOCK TABLES `salones` WRITE;
/*!40000 ALTER TABLE `salones` DISABLE KEYS */;
INSERT INTO `salones` VALUES (1,'Salon 306',40,1,'306','Edificio A',NULL);
/*!40000 ALTER TABLE `salones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `secciones`
--

DROP TABLE IF EXISTS `secciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `secciones` (
  `id_seccion` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id_seccion`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `secciones`
--

LOCK TABLES `secciones` WRITE;
/*!40000 ALTER TABLE `secciones` DISABLE KEYS */;
INSERT INTO `secciones` VALUES (1,'A'),(2,'B'),(3,'C'),(4,'D');
/*!40000 ALTER TABLE `secciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sede_carrera`
--

DROP TABLE IF EXISTS `sede_carrera`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sede_carrera` (
  `id_sede_carrera` int NOT NULL AUTO_INCREMENT,
  `id_sede` int NOT NULL,
  `id_carrera` int NOT NULL,
  PRIMARY KEY (`id_sede_carrera`),
  KEY `id_sede` (`id_sede`),
  KEY `id_carrera` (`id_carrera`),
  CONSTRAINT `sede_carrera_ibfk_1` FOREIGN KEY (`id_sede`) REFERENCES `sedes` (`id_sede`) ON DELETE CASCADE,
  CONSTRAINT `sede_carrera_ibfk_2` FOREIGN KEY (`id_carrera`) REFERENCES `carreras` (`id_carrera`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sede_carrera`
--

LOCK TABLES `sede_carrera` WRITE;
/*!40000 ALTER TABLE `sede_carrera` DISABLE KEYS */;
INSERT INTO `sede_carrera` VALUES (1,1,1),(2,1,2);
/*!40000 ALTER TABLE `sede_carrera` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sedes`
--

DROP TABLE IF EXISTS `sedes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sedes` (
  `id_sede` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `direccion` text COLLATE utf8mb4_unicode_ci,
  `telefono` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_sede`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sedes`
--

LOCK TABLES `sedes` WRITE;
/*!40000 ALTER TABLE `sedes` DISABLE KEYS */;
INSERT INTO `sedes` VALUES (1,'UMG Boca del Monte',NULL,NULL),(2,'UMG Villa Nueva',NULL,NULL),(3,'UMG Antigua Guatemala',NULL,NULL);
/*!40000 ALTER TABLE `sedes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `id_persona` int NOT NULL,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ultimo_login` datetime DEFAULT NULL,
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `username` (`username`),
  KEY `id_persona` (`id_persona`),
  CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`id_persona`) REFERENCES `personas` (`id_persona`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,2,'admin@example.com','scrypt:32768:8:1$XqeGMgjrSfsSr2Ku$583b715fe67f2ddcf2b5c2f7e58bf964bf9aaecdecafc11f28adf980f95d1119d03dc81edb4461439eb883c4118e8da883c9908be35c1d9e21ebcd82d915d362',NULL),(2,3,'admin','scrypt:32768:8:1$EQSkR9wJ3pyuICJb$4afea7f1d02b49e1dfbb13b837f472ef8bc37d8a8f942258246599e801b2bcc0efbdaf3970f12e7d79d5f6c3d5901d4d74bf350252833b5dd5f3fc076c732f1a',NULL),(3,4,'admin1','scrypt:32768:8:1$Z038J4SluIhuEcvt$963758fbcfa61ee2f5e99fd29b6434885cc788fa97330c36916c4d25b639af1b2e870425e122d449ecac0db282c9a817de9ff8248040d41e212c47f943931c42',NULL);
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-27  7:58:49
