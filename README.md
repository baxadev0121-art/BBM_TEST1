# Buxoro Bilimdonlar Maktabi - Test Platformasi

Bu loyiha Buxoro Bilimdonlar maktabi uchun zamonaviy test platformasidir. Platform o'qituvchilar, o'quvchilar va administratorlar uchun mo'ljallangan.

## ✨ Asosiy Xususiyatlar

### 🔐 Xavfsizlik va Authentifikatsiya
- Maktab email domenida ro'yxatdan o'tish majburiy
- Administrator tomonidan tasdiqlash tizimi
- Rol-ga asoslangan ruxsatlar (admin, teacher, student)

### 👨‍🏫 O'qituvchilar uchun
- Test yaratish va tahrirlash
- Savollar qo'shish (bir javobli, ko'p javobli, matnli)
- Vaqt chegarasi belgilash
- Natijalarni ko'rish va eksport qilish
- O'quvchilar faoliyatini kuzatish

### 👨‍🎓 O'quvchilar uchun
- Testlarni topish va ishtirok etish
- Real vaqtda taymer
- Natijalarni ko'rish
- Progress tracking

### 👨‍💼 Administratorlar uchun
- Foydalanuvchilarni tasdiqlash
- Tizim statistikasi
- Barcha testlar va natijalarni boshqarish

### 🎨 Zamonaviy UI/UX
- Glassmorphism dizayn
- AOS animatsiyalar
- Mobile responsive
- Dark/Light mode support

## 🚀 Texnik Stack

### Backend
- **Django 5.2.5** - Asosiy framework
- **SQLite** - Ma'lumotlar bazasi
- **Django REST API** - API endpoints
- **Custom User Model** - Moslashtirilgan foydalanuvchi tizimi

### Frontend
- **HTML5/CSS3/JavaScript** - Asosiy frontend
- **Bootstrap 5.3.0** - CSS framework
- **AOS Library** - Animatsiyalar
- **Font Awesome** - Ikonkalar
- **Glassmorphism** - Zamonaviy dizayn uslubi

## 📦 O'rnatish

### 1. Loyihani klonlash
```bash
git clone <repository_url>
cd mytest
```

### 2. Virtual muhitni yaratish
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# yoki
venv\Scripts\activate  # Windows
```

### 3. Dependencies o'rnatish
```bash
pip install django
```

### 4. Ma'lumotlar bazasini sozlash
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Superuser yaratish
```bash
python manage.py createsuperuser
```

### 6. Sample ma'lumotlar yuklash (ixtiyoriy)
```bash
python create_sample_data.py
```

### 7. Serverni ishga tushirish
```bash
python manage.py runserver 0.0.0.0:8000
```

## 🔑 Demo Login Ma'lumotlari

Sample data yuklangandan so'ng quyidagi hisoblar mavjud:

```
Admin: admin / admin123
O'qituvchi: teacher1 / teacher123
O'quvchi: student1 / student123
Tasdiqlanmagan o'quvchi: student2 / student123
```

## 📱 Sahifalar va Funksionallik

### Asosiy sahifalar:
- **/** - Bosh sahifa
- **/login/** - Kirish
- **/signup/** - Ro'yxatdan o'tish
- **/dashboard/** - Dashboard (har bir rol uchun alohida)
- **/profile/** - Profil
- **/tests/** - Testlar ro'yxati
- **/test/{id}/** - Test ishlash
- **/admin/** - Django admin panel

### API Endpoints:
- **/api/tests/** - Testlar API
- **/api/questions/{test_id}/** - Test savollari
- **/api/submit-test/** - Test natijalarini yuborish
- **/api/user-profile/** - Foydalanuvchi profili

## 🏗️ Loyiha Strukturasi

```
mytest/
├── manage.py                 # Django management
├── create_sample_data.py     # Sample data script
├── mytest/                   # Asosiy Django settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                 # Foydalanuvchilar app
│   ├── models.py            # User, VerificationRequest
│   ├── views.py             # Auth views
│   ├── admin.py             # Admin interface
│   └── urls.py
├── tests_app/               # Testlar app
│   ├── models.py           # Test, Question, Choice, etc.
│   ├── views.py            # Test views va API
│   ├── admin.py            # Admin interface
│   └── urls.py
├── templates/              # HTML shablonlar
│   ├── base.html
│   ├── home.html
│   ├── accounts/
│   └── tests/
└── static/                 # Static files
    ├── css/
    ├── js/
    └── images/
```

## 🔧 Sozlamalar

### Email domenlarini sozlash
`accounts/models.py` faylida quyidagi email domenlarini o'zgartiring:
```python
ALLOWED_DOMAINS = {
    'student': 'student.buxorobilimdonlar.uz',
    'teacher': 'buxorobilimdonlar.uz',
    'admin': 'admin.buxorobilimdonlar.uz'
}
```

### Vaqt chegaralarini sozlash
`tests_app/models.py` faylida default vaqt chegaralarini o'zgartiring.

## 🚀 Deploy qilish

### Development server
```bash
python manage.py runserver 0.0.0.0:8000
```

### Production uchun tavsiyalar
1. **DEBUG = False** qiling `settings.py` da
2. **ALLOWED_HOSTS** ni to'g'ri sozlang
3. **PostgreSQL** yoki **MySQL** ishlatish tavsiya etiladi
4. **Gunicorn** yoki **uWSGI** ishlatish
5. **Nginx** yoki **Apache** reverse proxy sifatida
6. **SSL sertifikat** o'rnatish
7. **Static va media files** ni alohida serve qilish

## 🧪 Testing

```bash
python manage.py test
```

## 📝 Ma'lumotlar Modeli

### User Model
- Role-based system (student, teacher, admin)
- Email verification
- Student/Teacher specific fields

### Test System
- Test -> Questions -> Choices
- TestAttempt -> Answers
- Scoring system
- Time limits

## 🤝 Hissa qo'shish

1. Fork qiling
2. Feature branch yarating (`git checkout -b feature/AmazingFeature`)
3. O'zgarishlarni commit qiling (`git commit -m 'Add some AmazingFeature'`)
4. Branch ga push qiling (`git push origin feature/AmazingFeature`)
5. Pull Request oching

## 📄 Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.

## 📞 Aloqa

Loyiha haqida savollar yoki takliflar bo'lsa:
- Email: info@buxorobilimdonlar.uz
- Website: https://buxorobilimdonlar.uz

---

**Buxoro Bilimdonlar maktabi** - Ta'lim sifatini oshirish yo'lida! 🎓
