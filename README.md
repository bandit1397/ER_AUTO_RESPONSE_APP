#project/
 ├ app.py
 ├ requirements.txt
 ├ hospital.db (자동 생성)
 ├ templates/
 │    ├ hospital.html
 │    ├ control.html
 ├ static/
 │    ├ alert.mp3

 #7. 이 시스템 완성 특징
   ✔ 실시간
     polling 없음
     WebSocket 즉시 전달
   ✔ 병원 태블릿 최적화
    브라우저만 사용
    설치 없음
  ✔ 병원 10~100개 확장 가능
  ✔ 10분 자동 만료 구조

# render
1. render 사이트(https://render.com) 접속/get started/로그인 방식 선택(github 로 로그인)/권한 승인- 깃허브 선택- authorize render
2. 로그인 화면/New + 클릭 - web server 선택/githut 저장소 연결-내 프로젝트 연결
3. 서버설정/ name-내프로젝트 /region- singapore/branch-main 그대로/runtime-python 선택/build command-pip install -r requirements.txt/ start command-python app.py/ instance type-free
4. deploy-create seb service 클릭/

# https://er-auto-response-app.onrender.com/control
https://er-auto-response-app.onrender.com/hospital/B

#android studio
 app/manifests/androidManifest.xml
 app/kotlin+java/com.hospital.viewer/MainActivity
 app/res/layout/acrivity_main.xml

# UptimeRobot / get started free

# 안전화
UptimeRobot
+
self-ping
+
유료 Render(Always On)
