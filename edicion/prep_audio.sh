set -e
VOICE="highpass=f=75,adeclick,afftdn=nr=10:nf=-45:tn=1,deesser=i=0.35,acompressor=threshold=-22dB:ratio=2.3:attack=8:release=200:makeup=1.5"
PITCH="highpass=f=85,adeclick,afftdn=nr=12:nf=-48:tn=1,acompressor=threshold=-24dB:ratio=2.2:attack=10:release=220:makeup=1.5"
proc() { # in map filter out
  ffmpeg -v error -y -i "$1" -map "$2" -af "$3,aresample=48000" -ac 2 -c:a pcm_s16le "aud/tmp_$4.wav"
  I=$(ffmpeg -nostats -i "aud/tmp_$4.wav" -af ebur128 -f null - 2>&1 | grep -A1 "Integrated loudness" | grep "I:" | awk '{print $2}')
  G=$(python3 -c "print(-16-($I))")
  ffmpeg -v error -y -i "aud/tmp_$4.wav" -af "volume=${G}dB" -c:a pcm_f32le "aud/$4.wav"
  echo "$4 I=$I gain=$G"
}
proc "src/Voz en off Kodu.mp4" 0:a:0 "$VOICE" c_vkodu &
proc "src/Voz en off Testra.mp4" 0:a:0 "$VOICE" c_vtestra &
proc "src/Voz en off ECHO" 0:a:0 "$VOICE" c_vecho &
proc "src/Límites gratuitos de cada aplicación" 0:a:0 "$VOICE" c_limites &
wait
proc "src/Video PITCH Inicial.mov" 0:a:0 "$PITCH" c_ini &
proc "src/Video PITCH Final.mp4" 0:a:0 "$PITCH" c_fin &
proc "src/Video Kodu DEMO.mp4" 0:a:0 "anull" c_dkodu &
proc "src/Video testra DEMO.mp4" 0:a:0 "anull" c_dtestra &
wait
proc "src/Video Echo DEMO.mp4" 0:a:0 "anull" c_decho
proc "aud/music.wav" 0:a:0 "anull" c_music
rm -f aud/tmp_*.wav
