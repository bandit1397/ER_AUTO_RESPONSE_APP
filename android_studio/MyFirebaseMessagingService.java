package com.hospital.viewer;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;

import androidx.core.app.NotificationCompat;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public class MyFirebaseMessagingService extends FirebaseMessagingService {

    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {

        String title = "🚨 긴급 요청";
        String body = "새 요청";

        if(remoteMessage.getData().containsKey("title")){
            title = remoteMessage.getData().get("title");
        }

        if(remoteMessage.getData().containsKey("body")){
            body = remoteMessage.getData().get("body");
        }

        // =========================
        // 🔥 WakeLock
        // =========================
        PowerManager powerManager =
                (PowerManager)getSystemService(Context.POWER_SERVICE);

        PowerManager.WakeLock wakeLock =
                powerManager.newWakeLock(
                        PowerManager.PARTIAL_WAKE_LOCK,
                        "hospital:wakelock"
                );

        wakeLock.acquire(10000);

        // =========================
        // 🔥 Native MP3 재생
        // =========================
        MediaPlayer player = MediaPlayer.create(
                this,
                R.raw.alarm
        );

        if(player != null){

            player.setVolume(1.0f,1.0f);

            player.setOnCompletionListener(mp -> {
                mp.release();
            });

            player.start();
        }

        // =========================
        // 🔥 MainActivity 열기
        // =========================
        Intent intent =
                new Intent(this, MainActivity.class);

        intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK |
                Intent.FLAG_ACTIVITY_CLEAR_TOP
        );

        PendingIntent pendingIntent =
                PendingIntent.getActivity(
                        this,
                        0,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT |
                        PendingIntent.FLAG_IMMUTABLE
                );

        // =========================
        // 🔥 Notification Channel
        // =========================
        String channelId = "emergency_channel";

        NotificationManager manager =
                (NotificationManager)getSystemService(
                        Context.NOTIFICATION_SERVICE
                );

        if(Build.VERSION.SDK_INT >= Build.VERSION_CODES.O){

            NotificationChannel channel =
                    new NotificationChannel(
                            channelId,
                            "Emergency",
                            NotificationManager.IMPORTANCE_HIGH
                    );

            channel.enableVibration(true);

            channel.setLockscreenVisibility(
                    android.app.Notification.VISIBILITY_PUBLIC
            );

            Uri soundUri =
                    Uri.parse(
                            "android.resource://" +
                            getPackageName() +
                            "/" +
                            R.raw.alarm
                    );

            AudioAttributes audioAttributes =
                    new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_ALARM)
                            .build();

            channel.setSound(soundUri, audioAttributes);

            manager.createNotificationChannel(channel);
        }

        // =========================
        // 🔥 Notification 생성
        // =========================
        NotificationCompat.Builder builder =
                new NotificationCompat.Builder(this, channelId)
                        .setSmallIcon(R.mipmap.ic_launcher)
                        .setContentTitle(title)
                        .setContentText(body)
                        .setPriority(NotificationCompat.PRIORITY_MAX)
                        .setCategory(NotificationCompat.CATEGORY_ALARM)
                        .setAutoCancel(true)
                        .setContentIntent(pendingIntent)
                        .setFullScreenIntent(pendingIntent, true);

        manager.notify(1, builder.build());
    }
}
