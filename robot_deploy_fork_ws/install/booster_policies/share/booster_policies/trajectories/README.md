# Trajectories Directory

Place your trajectory JSON files here.

The trajectory file should follow the format defined in `utils.py`:

```json
{
  "joint_names": [
    "Left_Hip_Pitch", "Left_Knee_Pitch", "Left_Ankle_Pitch", 
    "Right_Hip_Pitch", "Right_Knee_Pitch", "Right_Ankle_Pitch"
  ],
  "trajectories": [
    {
      "start_frame": 0,
      "end_frame": 200,
      "joint_positions": [
        [-0.1, -0.75],   
        [0.2, 1.5],
        [-0.1, -0.75],
        [-0.1, -0.75],   
        [0.2, 1.5],
        [-0.1, -0.75]
      ]
    },
    {
      "start_frame": 201,
      "end_frame": 400,
      "joint_positions": [
        [-0.75, -0.1],   
        [1.5, 0.2],
        [-0.75, -0.1],
        [-0.75, -0.1],   
        [1.5, 0.2],
        [-0.75, -0.1]
      ]
    }
  ]
}
```

## Configuration

In `config/squat_agent_params.yaml`, set the `trajectory_path` parameter:

```yaml
trajectory_path: "trajectories/trajectory.json"
```

Or use an absolute path if you prefer:

```yaml
trajectory_path: "/absolute/path/to/trajectory.json"
```

