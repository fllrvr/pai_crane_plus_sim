# pai_crane_plus_sim

カメラ付きの CRANE+ V2 シミュレーション（Gazebo）で、データ収集から LeRobot での学習・推論までを行う環境です。

## 構成

このリポジトリに含まれるもの:

```
pai_crane_plus_sim/
├── docker/
│   ├── Dockerfile                # 自作イメージ pai-ros2-camera
│   └── camera_position.patch     # カメラ位置の変更（本家 crane_plus に当てる）
├── dataset/                      # データ（中身は git 管理外）
├── checkpoints/                  # 学習済みモデル（中身は git 管理外）
├── run_pai_camera_container.sh   # コンテナを起動する
├── README.md
└── .gitignore
```

セットアップで作られるもの（git 管理外）:

| パス | 内容 |
| --- | --- |
| `pai_training/` | 変換・学習・推論（[fllrvr/pai_training](https://github.com/fllrvr/pai_training)、別リポジトリ） |
| `pai_ws/` | teleop（[fllrvr/physicalai_teleop](https://github.com/fllrvr/physicalai_teleop)、別リポジトリ） |

このフォルダは、コンテナ内では `/workspace` にマウントされます。

## フォーク元と主な変更

`pai_training` と `physicalai_teleop` は、[matsuolab/pai_training](https://github.com/matsuolab/pai_training) と [matsuolab/physicalai_teleop](https://github.com/matsuolab/physicalai_teleop) をフォークして改良したものです。

主な変更:

- `pai_training`
  - カメラ画像への対応
  - データ変換の修正
  - Diffusion Policy の追加
- `physicalai_teleop`
  - 箱を初期位置に戻す機能
  - 対象の箱を本家 crane_plus の `aruco_cube_0` に変更

## セットアップ

ホスト（このフォルダ）で:

```bash
# イメージをビルド
docker build -t pai-ros2-camera docker/

# コンテナを起動
./run_pai_camera_container.sh
```

ブラウザで http://localhost:6080 を開くと、コンテナのデスクトップが表示されます。

以下はコンテナ内で初回だけ行います。

### pai_ws（teleop）

```bash
# teleop 用のワークスペースを作って physicalai_teleop を clone
mkdir -p /workspace/pai_ws/src && cd /workspace/pai_ws/src
git clone -b v1.0 https://github.com/fllrvr/physicalai_teleop.git

# teleop をビルド
cd /workspace/pai_ws && colcon build --symlink-install
```

### pai_training（変換・学習・推論）

```bash
# pai_training を clone（LeRobot のサブモジュールも一緒に）
cd /workspace
git clone --recursive -b v1.0 https://github.com/fllrvr/pai_training.git

# pixi をインストール
curl -fsSL https://pixi.sh/install.sh | bash
echo 'eval "$(pixi completion --shell bash)"' >> ~/.bashrc
source ~/.bashrc

# Python 環境を作る（pai_training のフォルダで実行）
cd /workspace/pai_training && pixi install
```

## 使い方

### データ収集（ROS 2）

ターミナルを3つ開き、それぞれで実行します。

```bash
# シミュレーション（カメラ付き）
ros2 launch crane_plus_gazebo crane_plus_with_table.launch.py use_camera:=true

# キーボードで操作（B で箱を初期位置に戻す）
ros2 run physicalai_teleop teleop_keyboard

# 記録（1 エピソードごとに ep0、ep1、… と名前を変える）
ros2 bag record -o /workspace/dataset/rosbags/pick_and_move_camera/ep0 /joint_states \
  /crane_plus_arm_controller/joint_trajectory \
  /crane_plus_gripper_controller/joint_trajectory \
  /image_raw
```

### 変換・学習・推論（pai_training）

```bash
cd /workspace/pai_training

# rosbag を LeRobot のデータセットに変換
pixi run convert

# 学習
pixi run train

# 推論（シミュレーションを起動した状態で）
pixi run infer --model-path <学習済みモデルのパス>
```

入出力のパスは `pai_training/configs/` の `conversion_config.yaml` と `train_config.yaml` で設定します。

各コマンドの詳しい使い方は [fllrvr/pai_training の README](https://github.com/fllrvr/pai_training#usage) を見てください。
