# ⚡ MOB STOCKER METADATA

**AI-Powered Metadata Generator & XMP Injector for Microstock Contributors**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.2-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Tentang Aplikasi

**Mob Stocker Metadata** adalah alat untuk kontributor microstock (Shutterstock, Adobe Stock, iStock) yang ingin menghemat waktu mengisi metadata (title, description, keywords) secara otomatis menggunakan **Google Gemini AI**, lalu **embed langsung ke file** (bukan sidecar).

### ✨ Fitur Utama

| Fitur | Keterangan |
|-------|-------------|
| 🤖 **AI Auto-Generate** | Google Gemini AI Vision menganalisis gambar dan menghasilkan metadata otomatis |
| 📝 **Manual Mode** | Bisa isi metadata sendiri jika tidak ingin pakai AI |
| 💾 **Embed Langsung** | Metadata XMP di-inject langsung ke file (JPG/PNG/EPS) |
| 📁 **Batch Process** | Upload hingga 10 file sekaligus |
| 🖼️ **Preview Thumbnail** | Preview untuk file JPG/PNG |
| 📏 **Batasan Microstock** | Title 100 chars, Description 150 chars, Keywords 49 items |
| 🎨 **UI 3 Kolom** | Layout modern, responsif, support mobile |

### 🖼️ Format Didukung

| Format | Metadata Injection |
|--------|---------------------|
| **JPG / PNG** | XMP injected langsung (Dublin Core schema) |
| **EPS** | XMP injected langsung via manipulasi teks PostScript |

---

## 🚀 Cara Penggunaan

### 1. Persiapan API Key

- Daftar gratis di [Google AI Studio](https://aistudio.google.com/)
- Klik "Get API Key" dan copy key-nya
- Paste di aplikasi → klik **SAVE**

### 2. Upload File

- Klik tombol **📁 Pilih File** atau drag & drop ke area upload
- Pilih file JPG/PNG/EPS (max 10 file)
- Preview thumbnail akan muncul untuk JPG/PNG

### 3. Generate Metadata (AI Mode)

- Klik tombol **🚀 START GENERATE**
- Tunggu 5-15 detik (AI menganalisis gambar)
- Title, description, keywords akan terisi otomatis

### 4. Atau Manual Mode

- Isi sendiri title, description, keywords di form yang tersedia
- Perhatikan batasan karakter (counter berjalan otomatis)

### 5. Embed Metadata

- Klik tombol **💾 EMBED**
- File akan terdownload dengan metadata yang sudah di-inject
- File siap upload ke Shutterstock/Adobe Stock

---

## 📏 Batasan Metadata

| Field | Batasan | Keterangan |
|-------|---------|-------------|
| **Title** | Max 100 karakter | Termasuk spasi |
| **Description** | Max 150 karakter | Termasuk spasi |
| **Keywords** | Max 49 keywords | Dipisah koma, tanpa spasi setelah koma |

---

## 🛠️ Teknologi

| Teknologi | Fungsi |
|-----------|--------|
| **Google Gemini AI Vision** | Analisis gambar & generate metadata |
| **Python Flask** | Backend server |
| **Pillow (PIL)** | Manipulasi gambar & inject XMP ke JPG/PNG |
| **PostScript Manipulation** | Inject XMP langsung ke file EPS |
| **XMP Dublin Core** | Standar metadata untuk microstock |

---

## 📁 Struktur Project
