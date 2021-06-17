# !/bin/bash

source /home/qtrobot/robot/autostart/qt_robot.inc
SCRIPT_NAME="gspeech_publisher_log"
LOG_FILE=$(prepare_logfile "$SCRIPT_NAME")

read -d '' SPEECHENV << EOF

source /home/qtrobot/catkin_ws/src/gspeech_publisher/.venv/bin/activate;
export GOOGLE_APPLICATION_CREDENTIALS="/home/qtrobot/catkin_ws/src/gspeech_publisher/service.json";
export PYTHONPATH="${PYTHONPATH}:/home/qtrobot/catkin_ws/devel/lib/python2.7/dist-packages";
python3 /home/qtrobot/catkin_ws/src/gspeech_publisher/src/gspeech_publisher.py;
EOF

exec echo "qtrobot" | sudo -kSi bash -c "$SPEECHENV"





