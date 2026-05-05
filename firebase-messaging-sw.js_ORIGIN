importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js');

firebase.initializeApp({

  apiKey: "AIzaSyDsJCi2FmnNxjze95RK9eqGcTWv8zdYNxQ",
  authDomain: "er-auto-response.firebaseapp.com",
  projectId: "er-auto-response",
  storageBucket: "er-auto-response.firebasestorage.app",
  messagingSenderId: "604456714636",
  appId: "1:604456714636:web:8d0e832013b5e2c60256a9"

});

const messaging = firebase.messaging();


// =========================
// 🔥 백그라운드 PUSH 수신
// =========================
messaging.onBackgroundMessage(function(payload) {

  console.log("FCM BACKGROUND:", payload);

  const title = payload.data?.title || "긴급 요청";

  const body = payload.data?.body || "";

  const hospital = payload.data?.hospital || "B";

  self.registration.showNotification(title, {

    body: body,

    icon: "/icon.png",

    badge: "/icon.png",

    requireInteraction: true,

    vibrate: [300,100,300,100,300],

    data: {
      url: "/hospital/" + hospital
    }

  });

});


// =========================
// 🔥 알림 클릭 시 APK/WebView 깨우기
// =========================
self.addEventListener("notificationclick", function(event) {

  event.notification.close();

  const targetUrl =
    event.notification.data?.url || "/hospital/B";

  event.waitUntil(

    clients.matchAll({
      type: "window",
      includeUncontrolled: true
    }).then(function(clientList) {

      // 기존 창 있으면 포커스
      for (const client of clientList) {

        if (client.url.includes("/hospital/")) {

          client.focus();

          client.navigate(targetUrl);

          return;
        }
      }

      // 없으면 새로 열기
      return clients.openWindow(targetUrl);

    })

  );

});
