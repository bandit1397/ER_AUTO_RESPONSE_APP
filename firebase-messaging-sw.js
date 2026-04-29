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

messaging.onBackgroundMessage(function(payload) {

  // 🔥 data 메시지 기준으로 변경
  const title = payload.data?.title || "알림";
  const body = payload.data?.body || "";

  self.registration.showNotification(title, {

    body: body,

    icon: "/icon.png",

    requireInteraction: true,   // 🔥 사용자가 닫기 전까지 유지

    vibrate: [300, 100, 300, 100, 300]

  });

});
