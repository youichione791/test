#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PET所見チェッカー
誤字・記載漏れをチェックするGUIアプリケーション
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import re
import os
import sys


class PETChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("PET所見チェッカー")
        self.root.geometry("900x700")
        
        # 設定ファイルの読み込み
        self.rules = self.load_rules()
        
        # 正規表現のコンパイル
        self.compiled_patterns = self.compile_patterns()
        
        # GUI構築
        self.create_widgets()
        
        # チェック実行フラグ
        self.checking = False
    
    def load_rules(self):
        """設定ファイルを読み込む"""
        # 実行ファイルのディレクトリを取得
        if getattr(sys, 'frozen', False):
            # PyInstallerでパッケージ化されている場合
            base_path = os.path.dirname(sys.executable)
        else:
            # 通常のPythonスクリプトとして実行されている場合
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        rules_path = os.path.join(base_path, 'checker_rules.json')
        
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("エラー", f"設定ファイルが見つかりません: {rules_path}")
            return self.get_default_rules()
        except json.JSONDecodeError as e:
            messagebox.showerror("エラー", f"設定ファイルの形式が正しくありません: {e}")
            return self.get_default_rules()
    
    def get_default_rules(self):
        """デフォルトのルールを返す"""
        return {
            "typos": [],
            "required_keywords": [],
            "required_patterns": [],
            "suvmax_check": {"enabled": False}
        }
    
    def compile_patterns(self):
        """正規表現パターンをコンパイル"""
        compiled = {}
        
        # 必須パターンのコンパイル
        if "required_patterns" in self.rules:
            for pattern_rule in self.rules["required_patterns"]:
                try:
                    compiled[pattern_rule["name"]] = re.compile(pattern_rule["pattern"])
                except re.error as e:
                    print(f"正規表現エラー: {pattern_rule['name']} - {e}")
        
        # SUVmaxチェックパターンのコンパイル
        if self.rules.get("suvmax_check", {}).get("enabled", False):
            try:
                compiled["suvmax"] = re.compile(self.rules["suvmax_check"]["pattern"])
                compiled["suvmax_keyword"] = re.compile(self.rules["suvmax_check"]["keyword"])
            except re.error as e:
                print(f"SUVmax正規表現エラー: {e}")
        
        return compiled
    
    def create_widgets(self):
        """GUIウィジェットを作成"""
        # タイトルラベル
        title_label = tk.Label(
            self.root,
            text="PET所見チェッカー",
            font=("Arial", 16, "bold"),
            pady=10
        )
        title_label.pack()
        
        # 説明ラベル
        info_label = tk.Label(
            self.root,
            text="所見文をペーストすると自動的にチェックが実行されます",
            font=("Arial", 10),
            fg="gray"
        )
        info_label.pack()
        
        # テキスト入力エリア
        text_frame = tk.Frame(self.root)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("MS Gothic", 11),
            undo=True
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # ペーストイベントのバインド
        self.text_area.bind("<<Paste>>", self.on_paste)
        self.text_area.bind("<Control-v>", self.on_paste)
        self.text_area.bind("<Command-v>", self.on_paste)  # Mac用
        
        # 手動チェックボタン
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)
        
        check_button = tk.Button(
            button_frame,
            text="チェック実行",
            command=self.run_check,
            font=("Arial", 11),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=5
        )
        check_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = tk.Button(
            button_frame,
            text="クリア",
            command=self.clear_text,
            font=("Arial", 11),
            bg="#f44336",
            fg="white",
            padx=20,
            pady=5
        )
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # ステータスバー
        self.status_bar = tk.Label(
            self.root,
            text="準備完了",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Arial", 10)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ハイライト用タグの設定
        self.text_area.tag_config("highlight", background="#FFFF00", font=("MS Gothic", 11, "bold"))
    
    def on_paste(self, event=None):
        """ペーストイベント時の処理"""
        # 少し遅延させてからチェックを実行(ペースト完了を待つ)
        self.root.after(100, self.run_check)
        return None  # イベントを継続
    
    def clear_text(self):
        """テキストをクリア"""
        self.text_area.delete("1.0", tk.END)
        self.status_bar.config(text="テキストをクリアしました")
    
    def run_check(self):
        """チェックを実行"""
        if self.checking:
            return
        
        self.checking = True
        self.status_bar.config(text="チェック中...")
        self.root.update()
        
        # 既存のハイライトをクリア
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        
        # テキストを取得
        text = self.text_area.get("1.0", tk.END)
        
        if len(text.strip()) == 0:
            self.status_bar.config(text="テキストが入力されていません")
            self.checking = False
            return
        
        # チェック実行
        issues_count = 0
        
        # 1. 誤字・表記ゆれチェック
        issues_count += self.check_typos(text)
        
        # 2. 必須キーワードチェック
        issues_count += self.check_required_keywords(text)
        
        # 3. 必須パターンチェック
        issues_count += self.check_required_patterns(text)
        
        # 4. SUVmaxチェック
        issues_count += self.check_suvmax(text)
        
        # ステータス更新
        if issues_count == 0:
            self.status_bar.config(text="✓ チェック完了: 問題は見つかりませんでした")
        else:
            self.status_bar.config(text=f"✓ チェック完了: {issues_count}件の問題を検出しました")
        
        self.checking = False
    
    def check_typos(self, text):
        """誤字・表記ゆれをチェック"""
        count = 0
        for typo in self.rules.get("typos", []):
            wrong = typo["wrong"]
            # テキスト内で誤字を検索
            start_pos = 0
            while True:
                pos = text.find(wrong, start_pos)
                if pos == -1:
                    break
                
                # ハイライト
                start_index = self.get_text_index(text, pos)
                end_index = self.get_text_index(text, pos + len(wrong))
                self.text_area.tag_add("highlight", start_index, end_index)
                
                count += 1
                start_pos = pos + len(wrong)
        
        return count
    
    def check_required_keywords(self, text):
        """必須キーワードをチェック"""
        count = 0
        for keyword_rule in self.rules.get("required_keywords", []):
            keyword = keyword_rule["keyword"]
            if keyword not in text:
                # キーワードが見つからない場合は、テキスト末尾に警告を表示
                # (実際には末尾をハイライトするのは難しいので、カウントのみ)
                count += 1
        
        return count
    
    def check_required_patterns(self, text):
        """必須パターンをチェック"""
        count = 0
        for pattern_rule in self.rules.get("required_patterns", []):
            pattern_name = pattern_rule["name"]
            if pattern_name in self.compiled_patterns:
                pattern = self.compiled_patterns[pattern_name]
                matches = pattern.finditer(text)
                for match in matches:
                    start_index = self.get_text_index(text, match.start())
                    end_index = self.get_text_index(text, match.end())
                    self.text_area.tag_add("highlight", start_index, end_index)
                    count += 1
        
        return count
    
    def check_suvmax(self, text):
        """SUVmax値の記載をチェック"""
        if not self.rules.get("suvmax_check", {}).get("enabled", False):
            return 0
        
        count = 0
        
        # SUVmaxキーワードが含まれているか確認
        if "suvmax_keyword" in self.compiled_patterns:
            keyword_pattern = self.compiled_patterns["suvmax_keyword"]
            keyword_matches = list(keyword_pattern.finditer(text))
            
            if keyword_matches and "suvmax" in self.compiled_patterns:
                value_pattern = self.compiled_patterns["suvmax"]
                value_matches = list(value_pattern.finditer(text))
                
                # SUVmaxキーワードがあるのに値が記載されていない場合
                if len(keyword_matches) > len(value_matches):
                    # 値が記載されていないSUVmaxをハイライト
                    for keyword_match in keyword_matches:
                        # この位置の近くに値があるか確認
                        has_value = False
                        for value_match in value_matches:
                            if abs(keyword_match.start() - value_match.start()) < 20:
                                has_value = True
                                break
                        
                        if not has_value:
                            start_index = self.get_text_index(text, keyword_match.start())
                            end_index = self.get_text_index(text, keyword_match.end())
                            self.text_area.tag_add("highlight", start_index, end_index)
                            count += 1
        
        return count
    
    def get_text_index(self, text, pos):
        """文字列位置をtkinterのインデックスに変換"""
        lines = text[:pos].split('\n')
        line_num = len(lines)
        col_num = len(lines[-1])
        return f"{line_num}.{col_num}"


def main():
    root = tk.Tk()
    app = PETChecker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
