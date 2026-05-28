
colcon build
source ~/.bashrc
ros2 run start_mtf run_mtf_client


ros2 run camera_nodes mtf_batch_analyze   --input "$HOME/Dokumente/Messungen/Yannis Wesser/mtf_messungen/2"   --recursive --overwrite 

cd src/match-PM-match_pm_ProMOC_Assembly/yannis_verification/start_mtf/start_mtf/

python3 mtf_auswertung.py



colcon build --packages-select start_mtf

ros2 run start_mtf verzeichnung 

cd ros2_ws
source ~/.bashrc
ros2 launch promoc_bringup optical_measurement_system.launch.py
