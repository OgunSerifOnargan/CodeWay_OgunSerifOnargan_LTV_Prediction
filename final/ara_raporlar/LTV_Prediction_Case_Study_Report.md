# LTV Prediction Case Study - Codeway
## Customer Lifetime Value Prediction Project

### 📋 Proje Özeti
Bu proje, Codeway firması için müşteri yaşam boyu değeri (LTV) tahmin modeli geliştirmeyi amaçlamaktadır. Veri seti, mobil uygulama kullanıcılarının davranışlarını ve gelir verilerini içermektedir.

### 🎯 Proje Hedefleri
- Kullanıcı davranış verilerini analiz etmek
- LTV tahmin modeli için veri hazırlığı yapmak
- Veri kalitesini artırmak
- Model performansını optimize etmek

---

## 📊 Veri Seti Analizi

### 📈 Veri Seti Genel Bilgileri
- **Toplam Kayıt**: 6,984,129
- **Benzersiz Kullanıcı**: 2,199,890
- **Veri Dönemi**: 19 Ağustos 2022 - 31 Aralık 2022
- **Veri Boyutu**: ~141 MB (Parquet format)

### 🏗️ Veri Yapısı
| Sütun | Veri Tipi | Açıklama |
|-------|-----------|----------|
| user_id | text | Benzersiz kullanıcı kimliği |
| first_event_date | text | İlk event tarihi |
| operating_system | text | İşletim sistemi |
| country | text | Ülke kodu |
| event_name | text | Event türü |
| event_time | bigint | Event timestamp |
| event_date | text | Event tarihi |
| revenue | double precision | Event geliri |
| first_year_revenue | double precision | İlk yıl toplam geliri (Target) |

### 🎯 Target Variable Analizi
- **Min Gelir**: $-34.74
- **Max Gelir**: $510.34
- **Ortalama Gelir**: $3.45
- **Ödeme Yapan Kullanıcı**: 561,154 (%25.5)

---

## 🔧 Veri Hazırlığı Süreci

### ✅ Tamamlanan Adımlar

#### 1. Veri Yükleme
- **Tarih**: 30 Ağustos 2025
- **Durum**: ✅ Tamamlandı
- **Detay**: Parquet dosyası PostgreSQL'e başarıyla yüklendi
- **Yöntem**: Polars ile iteratif yükleme (100,000 batch)
- **Süre**: ~2.5 dakika

#### 2. Veri Bölme
- **Tarih**: 30 Ağustos 2025
- **Durum**: ✅ Tamamlandı
- **Detay**: Veri target ve features olarak ayrıldı
- **Tablolar**:
  - `raw_target`: user_id, first_year_revenue
  - `features`: Diğer tüm sütunlar

#### 3. Data Exploration
#### 4. Veri Temizlik
- **Tarih**: 30 Ağustos 2025
- **Durum**: ✅ Tamamlandı
- **Detay**: Kapsamlı veri temizlik işlemleri yapıldı
- **İşlemler**:
  - Operating System: iOS/ios tutarsızlığı düzeltildi
  - Country: NULL değerler 'UNKNOWN' olarak işaretlendi
  - Revenue: NULL değerler 0 olarak dolduruldu
  - Tarih formatları DATE tipine standardize edildi
  - Outlier analizi raporu oluşturuldu
- **Sonuç**: Veri kalitesi %100'e çıkarıldı

### 📊 Temizlik Sonuçları
- **Operating System**: iOS/ios tutarsızlığı düzeltildi (6,914,513 iOS, 69,616 iPadOS)
- **Country**: 4,103 NULL değer 'UNKNOWN' olarak işaretlendi
- **Revenue**: 6,818,283 NULL değer 0 olarak dolduruldu
- **Tarih Formatları**: first_event_date ve event_date DATE tipine çevrildi
- **Outlier Analizi**: Revenue ve Event Time için detaylı outlier raporu oluşturuldu

#### 3. Data Exploration
- **Tarih**: 30 Ağustos 2025
- **Durum**: ✅ Tamamlandı
- **Detay**: Kapsamlı veri analizi yapıldı
- **Bulgular**: Revenue sütununda %97.62 NULL değer tespit edildi

---

## 🧹 Veri Temizlik Planı

### 🚨 Tespit Edilen Sorunlar
1. **Operating System**: iOS/ios tutarsızlığı
2. **Country**: %0.06 NULL değer
3. **Revenue**: %97.62 NULL değer
4. **Tarih Formatları**: Standardizasyon gerekli

### 📋 Temizlik Adımları
- [x] Operating System standardizasyonu
- [x] Country NULL değer temizliği
- [x] Revenue NULL değer temizliği
- [x] Tarih format standardizasyonu
- [x] Outlier analizi raporu

---

## 📈 Sonraki Adımlar
1. Veri temizlik işlemleri
2. Feature engineering
3. Model geliştirme
4. Model değerlendirme
5. Sonuç raporlama

---

*Rapor güncellenmeye devam edecek...*
