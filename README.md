

	# Tercih Danışmanı Chatbot Projesi

Bu proje, üniversite tercih sürecinde öğrencilere yardımcı olmak için geliştirilmiş bir danışman chatbot sistemidir. Kullanıcıdan üniversite, bölüm, şehir, puan gibi bilgileri nazikçe toplayan ve bu bilgilerle önerilerde bulunan bir yapay zeka asistanı içerir.

## Proje Yapısı	

- **actions/**: Chatbotun özel aksiyonlarını ve prompt şablonlarını içerir.
- **backend/**: PDF çıktıları ve statik dosyaları barındırır, API veya arka uç işlemleri için kullanılır.
- **frontend/**: Kullanıcı arayüzü (web uygulaması) dosyalarını içerir.
- **models/**: Eğitimli makine öğrenimi modelleri burada saklanır.
- **data/**: Rasa için eğitim verileri (nlu, stories, rules).
- **config.yml**: Rasa NLU ve politika ayarları.
- **domain.yml**: Chatbotun intent, entity, slot ve yanıtlarını tanımlar.
- **endpoints.yml**: Aksiyon sunucusu ve diğer servislerin adresleri.
- **credentials.yml**: Rasa'nın bağlanacağı platformların kimlik bilgileri.

## Kurulum

1. **Gereksinimler**
   - Python 3.8+
   - Rasa (>=3.1)
   - Gerekli Python paketleri (`pip install -r requirements.txt`)
   - Node.js ve npm (frontend için)

2. **Rasa Ortamı Kurulumu**
   ```bash
   pip install rasa
   rasa train
   rasa run actions &
   rasa shell
   ```

3. **Frontend Kurulumu**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Aksiyon Sunucusu**
   - `actions/` klasöründeki özel aksiyonlar için Rasa action server başlatılır:
   ```bash
   rasa run actions
   ```

## Kullanım

- Chatbot, kullanıcıdan şehir, bölüm, puan, sıralama gibi bilgileri toplar ve tercihlerle ilgili önerilerde bulunur.
- Sadece üniversiteler, bölümler ve şehirler hakkında bilgi verir.
- Yanıtlar Türkçe ve kullanıcı dostudur.

## Katkı
Katkıda bulunmak için lütfen bir fork oluşturun ve pull request gönderin.

## Lisans
Bu proje MIT lisansı ile lisanslanmıştır.


