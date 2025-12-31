import os
import pandas as pd
import gc
import folder_paths
from huggingface_hub import hf_hub_download

# 全局变量存储 DataFrame
_DANBOORU_DB = None
_IS_LOADING = False

class DanbooruTagsGenerator:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "operation": (["Load & Generate", "Unload Memory"], {"default": "Load & Generate"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "min_score": ("INT", {"default": 20, "min": 0, "max": 10000}),
                "allowed_ratings": ("STRING", {"default": "g, s, q, e", "placeholder": "g, s, q, e"}),
                "include_tags": ("STRING", {"multiline": True, "default": "1girl", "placeholder": "必含标签"}),
                "exclude_tags": ("STRING", {"multiline": True, "default": "comic, monochrome", "placeholder": "排除标签"}),
            },
            "optional": {
                "hf_repo_id": ("STRING", {"default": "deepghs/danbooru2024"}),
                "hf_filename": ("STRING", {"default": "metadata.parquet"}),
                "hf_token": ("STRING", {"default": "", "placeholder": "Optional: HuggingFace Token"}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "score", "danbooru_url", "rating")
    FUNCTION = "process"
    CATEGORY = "Danbooru Tlant"

    def unload_memory(self):
        global _DANBOORU_DB
        if _DANBOORU_DB is not None:
            print("🧹 [Danbooru Tlant] 正在卸载数据并释放内存...")
            del _DANBOORU_DB
            _DANBOORU_DB = None
            gc.collect()
            print("✅ [Danbooru Tlant] 内存已释放。")
        else:
            print("ℹ️ [Danbooru Tlant] 内存中没有数据，无需卸载。")

    def load_dataframe(self, file_path):
        global _DANBOORU_DB, _IS_LOADING
        
        if _DANBOORU_DB is not None:
            return _DANBOORU_DB
        
        if _IS_LOADING:
            raise Exception("正在加载数据中，请稍后再试...")

        _IS_LOADING = True
        try:
            print(f"📦 [Danbooru Tlant] 正在加载 Parquet: {file_path}")
            
            # 1. 不显式指定列，先读取所有列的Schema，防止'id'不存在导致报错
            # 但为了内存，我们还是得筛选。
            # 先尝试标准列名
            columns_to_load = ['tag_string', 'score', 'rating', 'id']
            
            try:
                df = pd.read_parquet(file_path, columns=columns_to_load)
            except Exception as col_err:
                print(f"⚠️ [Danbooru Tlant] 按指定列加载失败，尝试不指定列名加载 (可能 ID 是索引)... 错误: {col_err}")
                # 如果失败，可能是 'id' 列不存在（也许它是 index）
                # 我们只读核心列，不读 id
                fallback_cols = ['tag_string', 'score', 'rating']
                df = pd.read_parquet(file_path, columns=fallback_cols)

            # 去除空 tag
            df = df.dropna(subset=['tag_string'])
            
            _DANBOORU_DB = df
            
            print(f"✅ [Danbooru Tlant] 数据加载完毕，共 {len(df)} 条记录。")
            print(f"🔍 [Debug] 当前数据列名: {df.columns.tolist()}")
            
            return df
        except Exception as e:
            print(f"❌ [Danbooru Tlant] 加载 DataFrame 失败: {e}")
            raise e
        finally:
            _IS_LOADING = False

    def process(self, operation, seed, min_score, allowed_ratings, include_tags, exclude_tags, hf_repo_id, hf_filename, hf_token):
        # 1. 内存卸载逻辑
        if operation == "Unload Memory":
            self.unload_memory()
            return ("", 0, "", "")

        # 2. 路径处理
        base_model_dir = os.path.join(folder_paths.base_path, "models")
        danbooru_dir = os.path.join(base_model_dir, "danbooru")
        
        if not os.path.exists(danbooru_dir):
            os.makedirs(danbooru_dir, exist_ok=True)
            
        file_path = os.path.join(danbooru_dir, hf_filename)

        # 3. 下载逻辑
        if not os.path.exists(file_path):
            print(f"🚀 [Danbooru Tlant] 准备下载...")
            try:
                token = hf_token.strip() if hf_token.strip() != "" else None
                downloaded_path = hf_hub_download(
                    repo_id=hf_repo_id,
                    filename=hf_filename,
                    repo_type="dataset",
                    local_dir=danbooru_dir,
                    token=token,
                    local_dir_use_symlinks=False 
                )
                file_path = downloaded_path
            except Exception as e:
                error_msg = f"Download Failed: {str(e)}"
                print(f"❌ [Danbooru Tlant] {error_msg}")
                return (error_msg, 0, "", "")

        # 4. 加载数据
        try:
            df = self.load_dataframe(file_path)
        except Exception as e:
            return (f"Load Error: {str(e)}", 0, "", "")

        # 5. 筛选逻辑
        target_ratings = [r.strip() for r in allowed_ratings.split(',') if r.strip()]
        if not target_ratings: 
            target_ratings = ['g', 's', 'q', 'e']
        
        filtered = df[df['rating'].isin(target_ratings)]
        filtered = filtered[filtered['score'] >= min_score]

        inc_list = [t.strip() for t in include_tags.replace('\n', ',').split(',') if t.strip()]
        for tag in inc_list:
            filtered = filtered[filtered['tag_string'].str.contains(tag, regex=False)]

        exc_list = [t.strip() for t in exclude_tags.replace('\n', ',').split(',') if t.strip()]
        for tag in exc_list:
            filtered = filtered[~filtered['tag_string'].str.contains(tag, regex=False)]

        # 6. 随机抽取
        count = len(filtered)
        if count == 0:
            print("⚠️ [Danbooru Tlant] 未找到符合条件的图片。")
            return ("Tags not found matching criteria", 0, "No URL", "")

        # 使用 seed
        sample = filtered.sample(n=1, random_state=seed % (2**32)).iloc[0]

        # 7. 处理数据
        # Tag 处理
        raw_tags = sample['tag_string'].split(' ')
        processed_tags = [t.replace('_', ' ') for t in raw_tags if t.strip()]
        final_tags = ", ".join(processed_tags)

        # 获取 ID 和 URL (增加健壮性)
        image_score = int(sample['score'])
        image_rating = str(sample['rating'])
        
        image_id_val = 0 # 初始化防止 UnboundLocalError
        danbooru_url = ""

        try:
            # 策略A: 尝试从列中获取 'id'
            if 'id' in sample:
                image_id_val = int(sample['id'])
            # 策略B: 尝试从 Index 获取 (如果是 DataFrame 的索引)
            elif hasattr(sample, 'name'):
                print(f"ℹ️ [Debug] 'id' 列未找到，尝试使用索引: {sample.name}")
                image_id_val = int(sample.name)
            else:
                print("❌ [Debug] 无法在行数据中找到 ID 或 索引。")
                image_id_val = 0
            
            if image_id_val > 0:
                danbooru_url = f"https://danbooru.donmai.us/posts/{image_id_val}"
            else:
                danbooru_url = "ID not found"

        except Exception as e:
            print(f"❌ ID Logic Error: {e}")
            danbooru_url = "Error generating URL"

        print(f"🎯 [Danbooru Tlant] 选中 ID: {image_id_val}, Rating: {image_rating}, Score: {image_score}")
        
        return (final_tags, image_score, danbooru_url, image_rating)

NODE_CLASS_MAPPINGS = {
    "DanbooruRandomTagsGeneratorTlant": DanbooruTagsGenerator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DanbooruRandomTagsGeneratorTlant": "Danbooru Tags Generator (Tlant)"
}