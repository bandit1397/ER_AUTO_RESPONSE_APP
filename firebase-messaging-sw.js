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

  self.registration.showNotification(
    payload.notification.title,
    {
      body: payload.notification.body
    }
  );

});
