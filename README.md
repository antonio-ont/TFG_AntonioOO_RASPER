# RASPER: Robot Móvil con ROS 2 Humble y Raspberry Pi 4

Este repositorio contiene la pila de control para **RASPER** (Raspberry Actuated Servo Platform for Educational Robotics), un robot diferencial modular y de bajo coste. Soporta tanto el control del robot físico real mediante una Raspberry Pi 4 B como su ejecución en un entorno de simulación 3D (Gazebo Classic 11) bajo Windows 11 y WSL2.

---

## 🛠️ Requisitos Rápidos

* **Robot Real**: Raspberry Pi 4 B (Ubuntu 22.04 LTS), Adafruit PCA9685 PWM HAT (I2C), 2 servomotores de rotación continua (canal 7 izquierdo, canal 8 derecho), baterías separadas para lógica y potencia.
* **Simulación**: Windows 11 + WSL2 (Ubuntu 22.04 LTS) con aceleración gráfica activa (WSLg) y Gazebo Classic 11.

---

## ⚙️ 1. Compilación del Workspace (Común)

Tanto en la Raspberry Pi 4 como en el entorno WSL2, clona el repositorio, navega a tu espacio de trabajo y compila los paquetes:

```bash
cd ~/robot_ws
colcon build --symlink-install
source install/setup.bash
```

---

## 🤖 2. Arrancar el Robot Real

Sigue estos pasos en la terminal SSH de tu Raspberry Pi:

1. **Verificar comunicación I2C**:
   ```bash
   sudo i2cdetect -y 1
   ```
   *Debe aparecer `40` en la dirección `0x40`. Si no aparece, habilita el bus serie I2C mediante `sudo raspi-config` (Interface Options -> I2C) y revisa el conexionado.*

2. **Lanzar el nodo de control y Rosbridge**:
   ```bash
   ros2 launch robot_driver robot.launch.py
   ```

3. **Lanzar la interfaz web (PWA)**:
   ```bash
   cd ~/robot_ws/app
   python3 -m http.server 8080
   ```
   *Abre `http://<IP_DE_LA_PI>:8080` en tu móvil o PC conectado a la misma red WiFi. Ve a Ajustes (⚙️), introduce la IP de la Pi y el puerto `9090`, y pulsa **Conectar**.*

---

## 💻 3. Arrancar la Simulación (WSL2)

En la terminal de WSL2 de tu ordenador:

1. **Verificar aceleración 3D (WSLg)**:
   ```bash
   glxinfo | grep "direct rendering" # Debe responder: direct rendering: Yes
   ```

2. **Lanzar simulación unificada**:
   ```bash
   ros2 launch robot_driver simulation.launch.py
   ```

3. **Controlar desde la Web**:
   * Abre el archivo `app/index.html` en el navegador de tu PC Windows.
   * Entra a Ajustes (⚙️), pon `localhost` y el puerto `9090`, y pulsa **Conectar**.

---

## ⚠️ Resolución de Problemas y Fallos Comunes

### A. Fallo de permisos I2C en la Raspberry Pi
* **Error**: `Permission denied` al intentar abrir `/dev/i2c-1`.
* **Solución**: Añade tu usuario al grupo de acceso del bus serie de forma permanente:
  ```bash
  sudo usermod -aG i2c $USER
  newgrp i2c
  ```
  *(O de forma temporal para pruebas rápidas: `sudo chmod 666 /dev/i2c-1`)*.

### B. El robot no aparece en Gazebo (`Service /spawn_entity unavailable` o Timeout)
* **Causa**: Gazebo Classic intenta conectarse a un servidor de base de datos de modelos online que ya no funciona.
* **Solución**: Detén todas las tareas colgadas e inicia de nuevo estableciendo la variable de base de datos a vacío:
  ```bash
  killall -9 gzserver gzclient && pkill -9 -f gazebo
  export GAZEBO_MODEL_DATABASE_URI=""
  ros2 launch robot_driver simulation.launch.py
  ```

### C. El robot no se mueve en línea recta o gira al revés (Robot Real)
* **Solución**: Ajusta por software los parámetros del nodo en su arranque:
  * Modifica `trim_left` y `trim_right` para ajustar el punto muerto exacto de los servos y evitar el desplazamiento en reposo (*creeping*).
  * Cambia `invert_left` o `invert_right` a `True` / `False` en tu launch si alguna rueda tracciona al revés.

### D. Rendimiento gráfico lento o pantalla en negro en WSL2
* **Solución**: Fuerza el renderizado gráfico por software en la CPU ejecutando antes del launch:
  ```bash
  export LIBGL_ALWAYS_SOFTWARE=1
  ```
