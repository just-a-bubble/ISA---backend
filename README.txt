-----------STRUKTURA PROJEKTA--------------
korenska mapa
I  backend/
I   - main.py, requirements.txt, Dockerfile 
I
I  frontend/ 
I   - index.html, login.html, register.html, style.css
I
I  nginx/
I   - default.conf
I
I  recepti_app/
I   – Flutter aplikacija (vse kar je v "ISA---recepti_app-flutter" repozitoriju)
I
I  docker-compose.yml  (definicija storitev)
I
I  skupno.db3 – podatkovna baza (dosegljiva na Google Drive)


!!!!!!!POZOR!!!!!! - Projekt ne bo deloval, če struktura datotek ni identična kot prikazana zgoraj


-----------PODATKOVNA BAZA--------------
Datoteko skupno.db3 prenesi s Google Drive in jo postavi v koren projekta, kjer je docker-compose.yml
Google Drive link: https://drive.google.com/file/d/1Oe-uKiFqInHPzyS-pJUb9_zYwzAS6auZ/view?usp=sharing


----------ZAGON DOCKER APLIKACIJE--------------
Odpri terminal v korenski mapi projekta (kjer je docker-compose.yml).
Zaženi projekt z ukazom: docker-compose up --build

Backend bo dosegljiv na http://localhost:8000
Frontend bo dosegljiv na http://localhost:8080
API dokumentacije bo dosegljiva na http://localhost:8080/api/docs


----------ZAGON FLUTTER APLIKACIJE--------------
1. Prepričaj se, da imaš nameščen Flutter SDK
2. Odprite terminal v mapi recepti_app
3. Generirajte APK za Android z ukazom: flutter build apk --release

4. APK datoteko prenesite na telefon in jo namestite

!!!!!Že pripravljena apk datoteka, ki se jo lahko prenese na telefon in instalira, se nahaja v recepti_app\build\app\outputs\flutter-apk\app-release.apk
