import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

def visualize_attendance(attendance):
    days = list(attendance.keys())
    counts = list(attendance.values())

    # 日本語フォントを設定
    script_dir = os.path.dirname(os.path.abspath(__file__))  # スクリプトのディレクトリを取得
    font_path = os.path.join(script_dir, 'NotoSansJP-VariableFont_wght.ttf')  # フォントファイルへの相対パス
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = prop.get_name()
    plt.rcParams['font.sans-serif'] = [prop.get_name()]
    plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の問題を解決するため

    plt.figure(figsize=(10, 5))
    plt.bar(days, counts, color='blue')
    plt.xlabel('曜日', fontproperties=prop)
    plt.ylabel('選択数', fontproperties=prop)
    plt.title('集計結果', fontproperties=prop)
    plt.xticks(fontproperties=prop)  # X軸のラベルにフォントを適用
    plt.yticks(fontproperties=prop)  # Y軸のラベルにフォントを適用
    plt.savefig('attendance.png')
    plt.close()