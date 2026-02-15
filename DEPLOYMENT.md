# 🚀 Инструкция по деплою TaskFlow на VPS

## Вариант 1: Ubuntu Server (DigitalOcean, Linode, Hetzner)

### 1. Создайте VPS
- **DigitalOcean**: https://www.digitalocean.com/ (от $4/месяц)
- **Hetzner**: https://www.hetzner.com/ (от €3.79/месяц)
- **Linode**: https://www.linode.com/ (от $5/месяц)

Рекомендуемая конфигурация:
- OS: Ubuntu 22.04 LTS
- RAM: минимум 1GB (рекомендуется 2GB)
- CPU: 1 core
- Storage: 25GB

### 2. Подключитесь к серверу

```bash
ssh root@your-server-ip
```

### 3. Обновите систему

```bash
apt update && apt upgrade -y
```

### 4. Установите Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt install docker-compose -y

# Проверка установки
docker --version
docker-compose --version
```

### 5. Создайте пользователя для приложения

```bash
# Создайте пользователя
adduser taskflow

# Добавьте в группу docker
usermod -aG docker taskflow

# Переключитесь на пользователя
su - taskflow
```

### 6. Загрузите проект на сервер

**Вариант A: Через Git (рекомендуется)**

```bash
# Установите git (если нужно, под root)
# exit
# apt install git -y
# su - taskflow

# Клонируйте репозиторий
git clone https://github.com/yourusername/taskflow.git
cd taskflow
```

**Вариант B: Через SCP (с вашего компьютера)**

```bash
# На вашем компьютере (Windows PowerShell)
scp -r E:\pycharm\taskflow_django\taskmanager taskflow@your-server-ip:~/
```

### 7. Настройте переменные окружения

```bash
cd ~/taskmanager

# Скопируйте пример
cp .env.example .env

# Отредактируйте файл
nano .env
```

Замените значения:
```env
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

DB_NAME=taskflow_db
DB_USER=taskflow_user
DB_PASSWORD=STRONG_PASSWORD_HERE
DB_HOST=db
DB_PORT=5432
```

Сгенерируйте SECRET_KEY:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 8. Обновите конфигурацию Nginx

```bash
nano nginx.conf
```

Замените `your-domain.com` на ваш реальный домен или IP адрес.

### 9. Сделайте скрипт деплоя исполняемым

```bash
chmod +x deploy.sh
```

### 10. Запустите деплой

```bash
./deploy.sh
```

### 11. Создайте первого администратора

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Или заполните демо-данными:

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py seed_data
```

### 12. Проверьте работу

Откройте в браузере: `http://your-server-ip`

---

## Настройка домена и SSL (HTTPS)

### 1. Настройте DNS

В настройках вашего домена (Namecheap, GoDaddy, Cloudflare) создайте A-записи:

```
Type    Name    Value
A       @       your-server-ip
A       www     your-server-ip
```

### 2. Получите SSL сертификат (Let's Encrypt)

```bash
# Установите Certbot
sudo apt install certbot -y

# Остановите Nginx
docker-compose -f docker-compose.prod.yml stop nginx

# Получите сертификат
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Перезапустите контейнеры
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Обновите nginx.conf

Раскомментируйте HTTPS блок в `nginx.conf` и обновите домен:

```bash
nano nginx.conf
```

Перезапустите Nginx:

```bash
docker-compose -f docker-compose.prod.yml restart nginx
```

### 4. Автообновление сертификата

```bash
# Добавьте в crontab
sudo crontab -e

# Добавьте строку:
0 3 * * * certbot renew --quiet && docker-compose -f /home/taskflow/taskmanager/docker-compose.prod.yml restart nginx
```

---

## Обновление приложения

```bash
cd ~/taskmanager

# Получите последние изменения (если используете Git)
git pull

# Запустите деплой
./deploy.sh
```

---

## Полезные команды

**Просмотр логов:**
```bash
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f db
```

**Перезапуск сервисов:**
```bash
docker-compose -f docker-compose.prod.yml restart
```

**Остановка:**
```bash
docker-compose -f docker-compose.prod.yml down
```

**Вход в контейнер:**
```bash
docker-compose -f docker-compose.prod.yml exec web bash
docker-compose -f docker-compose.prod.yml exec db psql -U taskflow_user -d taskflow_db
```

**Резервное копирование БД:**
```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U taskflow_user taskflow_db > backup_$(date +%Y%m%d).sql
```

**Восстановление БД:**
```bash
cat backup_20260211.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U taskflow_user taskflow_db
```

---

## Мониторинг

**Использование ресурсов:**
```bash
docker stats
```

**Свободное место:**
```bash
df -h
```

**Память:**
```bash
free -h
```

---

## Безопасность

### 1. Настройте firewall

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 2. Отключите вход по паролю SSH

```bash
sudo nano /etc/ssh/sshd_config
```

Установите:
```
PasswordAuthentication no
```

Перезапустите SSH:
```bash
sudo systemctl restart ssh
```

### 3. Регулярно обновляйте систему

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Вариант 2: PaaS (Проще, но дороже)

### Railway (https://railway.app/)
- Бесплатно: 500 часов/месяц
- Автоматический деплой из Git
- Встроенная PostgreSQL
- HTTPS из коробки

### Render (https://render.com/)
- Бесплатный план
- Автоматический деплой
- Встроенная PostgreSQL
- HTTPS из коробки

### Heroku (https://heroku.com/)
- $5-7/месяц
- Простой деплой
- Много аддонов

---

## Рекомендации по выбору

**VPS (DigitalOcean/Hetzner)** - если:
✅ Хотите полный контроль
✅ Планируете масштабирование
✅ Нужна максимальная производительность за деньги

**PaaS (Railway/Render)** - если:
✅ Нужен быстрый старт
✅ Не хотите настраивать сервер
✅ Готовы платить больше за удобство

---

Нужна помощь с конкретным шагом? Спрашивайте!
