#%%
"""Summarize the collected episodes.

1. Episode lengths and image rates, read from the rosbags (dataset/rosbags/pick_and_move_camera).
   Uses only the standard library, so this part also runs on the host.
2. Time the joints (observation.state) and the teleop commands (action) are stopped,
   read from the converted LeRobot dataset (dataset/lerobot_dataset/crane_plus_pick_and_move_camera).
   Needs numpy and pandas, which are imported in that cell.

Run in the container after `pixi run convert`:
    cd /workspace/pai_training && pixi run python /workspace/notebooks/check_data.py
Each `#%%` block can also be run as a cell in the VS Code interactive window.

The episode_index of the LeRobot dataset follows the rosbag folder names sorted as strings
(ep0, ep1, ep10, ...), so both tables show the rosbag name and the episode_index.
"""
import sqlite3
from pathlib import Path

try:
    REPO_ROOT = Path(__file__).resolve().parents[1]
except NameError:  # Interactive window: the working directory is notebooks/
    REPO_ROOT = Path.cwd().parent
BAG_DIR = REPO_ROOT / "dataset" / "rosbags" / "pick_and_move_camera"
IMAGE_TOPIC = "/image_raw"
LEROBOT_DIR = REPO_ROOT / "dataset" / "lerobot_dataset" / "crane_plus_pick_and_move_camera"
# Episode folders in the order rosbag2lerobot.py numbers them (episode_index):
# sorted as strings, so ep10 comes before ep2
EPISODE_DIRS = sorted(p.parent for p in BAG_DIR.rglob("*.db3"))


def read_episode(db3_path):
    """Return the duration [s] and the number of messages per topic of one rosbag2 file."""
    con = sqlite3.connect(f"file:{db3_path}?mode=ro", uri=True)
    try:
        start, end = con.execute("SELECT MIN(timestamp), MAX(timestamp) FROM messages").fetchone()
        counts = dict(con.execute(
            "SELECT topics.name, COUNT(*) FROM messages"
            " JOIN topics ON messages.topic_id = topics.id GROUP BY topics.name"
        ).fetchall())
    finally:
        con.close()
    return (end - start) / 1e9, counts


#%%
# エピソードの長さを確認する
episodes = []
for ep_dir in sorted(EPISODE_DIRS, key=lambda p: (len(p.name), p.name)):
    duration, counts = read_episode(sorted(ep_dir.glob("*.db3"))[0])
    episodes.append((ep_dir.name, EPISODE_DIRS.index(ep_dir), duration, counts.get(IMAGE_TOPIC, 0)))

print(f"{'rosbag':<8} {'episode_index':>13} {'長さ [s]':>9} {'画像の枚数':>9} {'画像 [Hz]':>9}")
for name, index, duration, n_images in episodes:
    print(f"{name:<8} {index:>13} {duration:>9.1f} {n_images:>9} {n_images / duration:>9.1f}")

durations = [d for _, _, d, _ in episodes]
print()
print(f"エピソード数: {len(durations)}")
print(f"合計: {sum(durations):.1f} s（{sum(durations) / 60:.1f} 分）")
print(f"平均: {sum(durations) / len(durations):.1f} s、最短: {min(durations):.1f} s、最長: {max(durations):.1f} s")


#%%
# 関節が停止している時間を確認する
# Uses the LeRobot dataset (20 Hz). pandas is only in the pixi environment, so run this in the container:
#   cd /workspace/pai_training && pixi run python /workspace/notebooks/check_data.py
import numpy as np
import pandas as pd

FPS = 20
# A joint counts as stopped while it moves less than this per frame (0.001 rad / 0.05 s = about 1 deg/s)
STATE_EPS = 1e-3
# Ignore stops shorter than this
MIN_STOP_S = 0.5


def stop_segments(values, eps):
    """Return (start, end) frame indices of the runs where no element changes by more than eps."""
    moving = np.abs(np.diff(values, axis=0)).max(axis=1) > eps
    stopped = np.concatenate([[False], ~moving, [False]])
    edges = np.flatnonzero(np.diff(stopped.astype(int)))
    segments = edges.reshape(-1, 2)
    return [(start, end) for start, end in segments if (end - start) / FPS >= MIN_STOP_S]


def summarize(segments, n_frames):
    """Split the stopped time [s] into the start, the middle and the end of the episode."""
    head = tail = middle = 0.0
    longest_middle = 0.0
    for start, end in segments:
        length = (end - start) / FPS
        if start == 0:
            head += length
        elif end >= n_frames - 1:
            tail += length
        else:
            middle += length
            longest_middle = max(longest_middle, length)
    return head, middle, tail, longest_middle


rows = []
for path in sorted((LEROBOT_DIR / "data").glob("chunk-*/episode_*.parquet")):
    df = pd.read_parquet(path)
    n_frames = len(df)
    episode_index = int(df["episode_index"].iloc[0])
    for name, column, eps in [("関節", "observation.state", STATE_EPS), ("指令", "action", 0.0)]:
        values = np.stack(df[column].to_numpy())
        head, middle, tail, longest = summarize(stop_segments(values, eps), n_frames)
        rows.append({
            "episode": episode_index,
            "rosbag": EPISODE_DIRS[episode_index].name,
            "対象": name,
            "長さ [s]": n_frames / FPS,
            "最初 [s]": head,
            "途中 [s]": middle,
            "最後 [s]": tail,
            "途中の最長 [s]": longest,
            "停止の割合 [%]": 100 * (head + middle + tail) / (n_frames / FPS),
        })

stops = pd.DataFrame(rows)
pd.set_option("display.width", 200)
for name, group in stops.groupby("対象", sort=False):
    print(f"--- {name}（{'関節の角度' if name == '関節' else 'teleop の指令値'}が止まっている時間）")
    print(group.drop(columns="対象").round(1).to_string(index=False))
    print(group.drop(columns=["対象", "episode", "rosbag"]).mean().round(1).to_frame("平均").T.to_string())
    print()