"""CLI 入口：编排整个蒸馏管线"""

from __future__ import annotations

import json
from pathlib import Path

import click

from src.utils.config import Config
from src.utils.llm_client import MultiLLMClient
from src.book_parser import BookParser, MethodologyExtractor
from src.tweet_scraper import TweetScraper
from src.distiller import JointDistiller
from src.skill_renderer import SkillRenderer


@click.group()
def cli():
    """书 + 推文联合蒸馏管线"""


@cli.command()
@click.option("--config", "-c", default=None, help="配置文件路径")
@click.option("--output", "-o", default=None, help="输出目录")
def status(config, output):
    """检查配置和依赖状态"""
    cfg = Config.load(Path(config) if config else None)

    click.echo("[配置状态]\n")

    # 书
    if cfg.book.is_configured():
        click.echo(f"  [书] {cfg.book.path or cfg.book.url} -- 已配置")
    else:
        click.echo("  [书] 未配置 (将跳过)")

    # 推文
    if cfg.twitter.is_configured():
        click.echo(f"  [推文] @{cfg.twitter.username} ({cfg.twitter.max_tweets} 条) -- 已配置")
    else:
        click.echo("  [推文] 未配置 (将跳过)")

    # LLM 提供商
    if cfg.llm.is_configured():
        providers = cfg.llm.configured_providers
        for p in providers:
            click.echo(f"  [LLM] {p.name}: {p.model} ({p.api_base})")
    else:
        click.echo("  [LLM] 未配置任何 API 提供商")

    click.echo(f"\n  [输出目录] {cfg.output.dir}")


@cli.command()
@click.option("--config", "-c", default=None, help="配置文件路径")
@click.option("--skip-book", is_flag=True, help="跳过书解析")
@click.option("--skip-tweets", is_flag=True, help="跳过推文采集")
@click.option("--tweet-file", "-t", default=None, help="使用已有推文文件(JSONL)")
@click.option("--output", "-o", default=None, help="输出目录")
def run(config, skip_book, skip_tweets, tweet_file, output):
    """执行完整蒸馏管线"""
    cfg = Config.load(Path(config) if config else None)
    if output:
        cfg.output.dir = output

    output_dir = Path(cfg.output.dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 初始化多模型 LLM
    llm = MultiLLMClient(cfg.llm)
    click.echo(f"  使用 {llm.count} 个模型: {', '.join(llm.provider_names)}")

    # ── Phase 1: 书解析 ──
    book_skeletons = []
    if not skip_book and cfg.book.is_configured():
        click.echo("\n[Phase 1a] 解析书...")
        parser = BookParser(cfg.book)
        chapters = parser.extract_text()
        click.echo(f"   -> 提取了 {len(chapters)} 个章节")

        click.echo("\n[Phase 1b] 提取方法论骨架...")
        extractor = MethodologyExtractor(llm)
        book_skeletons = extractor.extract(chapters)
        click.echo(f"   -> 提取了 {len(book_skeletons)} 章骨架")

        # 保存中间结果
        skeleton_path = output_dir / cfg.output.book_skeleton
        with open(skeleton_path, "w", encoding="utf-8") as f:
            json.dump(book_skeletons, f, ensure_ascii=False, indent=2)
        click.echo(f"   -> 骨架已保存到 {skeleton_path}")
    else:
        # 尝试从文件读取
        skeleton_path = output_dir / cfg.output.book_skeleton
        if skeleton_path.exists():
            with open(skeleton_path, encoding="utf-8") as f:
                book_skeletons = json.load(f)
            click.echo(f"[书] 从文件加载了 {len(book_skeletons)} 章骨架")

    # ── Phase 2: 推文采集与分析 ──
    tweet_findings = []
    tweets = []

    if not skip_tweets:
        if tweet_file:
            # 从文件加载
            tweets = TweetScraper.load_from_file(Path(tweet_file))
            click.echo(f"\n[推文] 从文件加载了 {len(tweets)} 条推文")
        elif cfg.twitter.is_configured():
            click.echo(f"\n[Phase 2a] 采集推文 (@{cfg.twitter.username})...")
            scraper = TweetScraper(cfg.twitter)
            tweets_path = output_dir / "raw_tweets.jsonl"
            tweets = scraper.scrape(output_path=tweets_path)
        else:
            click.echo("\n[推文] 配置未提供，跳过")

        if tweets:
            click.echo(f"\n[Phase 2b] LLM 开放式发现 ({len(tweets)} 条)...")
            distiller = JointDistiller(llm)
            tweet_findings = distiller.discover_from_tweets(tweets)

            # 保存推文分析结果
            findings_path = output_dir / cfg.output.tweet_findings
            with open(findings_path, "w", encoding="utf-8") as f:
                for finding in tweet_findings:
                    f.write(json.dumps(finding, ensure_ascii=False) + "\n")
            click.echo(f"   -> 推文分析已保存到 {findings_path}")
    else:
        # 尝试从文件加载
        findings_path = output_dir / cfg.output.tweet_findings
        if findings_path.exists():
            with open(findings_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        tweet_findings.append(json.loads(line))
            click.echo(f"[推文] 从文件加载了 {len(tweet_findings)} 批推文分析")

    # ── Phase 3: 交叉验证 ──
    if book_skeletons and tweet_findings:
        click.echo("\n[Phase 3] 交叉验证...")
        distiller = JointDistiller(llm)
        cross_result = distiller.cross_validate(book_skeletons, tweet_findings)

        cv_path = output_dir / cfg.output.cross_validation
        with open(cv_path, "w", encoding="utf-8") as f:
            json.dump(cross_result, f, ensure_ascii=False, indent=2)
        click.echo(f"   -> 交叉验证已保存到 {cv_path}")

        # ── Phase 4: 生成 SKILL.md ──
        click.echo("\n[Phase 4] 生成 SKILL.md...")
        renderer = SkillRenderer(llm)
        skill_path = output_dir / cfg.output.final_skill
        renderer.render(
            cross_validation=cross_result,
            book_skeletons=book_skeletons,
            tweet_findings=tweet_findings,
            persona_name=f"@{cfg.twitter.username} 分析方法" if cfg.twitter.username else "分析方法",
            output_path=skill_path,
        )

        click.echo(f"\n[完成] 所有输出在 {output_dir}/")
    elif not book_skeletons and not tweet_findings:
        click.echo("\n[跳过] 书和推文都没有提供数据。请配置 settings.local.yaml 后再运行。")
    elif not book_skeletons:
        click.echo("\n[跳过] 只有推文数据，没有书。已跳过交叉验证和 SKILL 生成。")
    else:
        click.echo("\n[跳过] 只有书数据，没有推文。已跳过交叉验证和 SKILL 生成。")


@cli.command()
@click.option("--config", "-c", default=None, help="配置文件路径")
def scrape_only(config):
    """仅执行推文采集"""
    cfg = Config.load(Path(config) if config else None)

    if not cfg.twitter.is_configured():
        click.echo("[错误] 请先设置 twitter.username")
        return

    output_dir = Path(cfg.output.dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tweets_path = output_dir / "raw_tweets.jsonl"

    scraper = TweetScraper(cfg.twitter)
    tweets = scraper.scrape(output_path=tweets_path)
    click.echo(f"[完成] 采集完成: {len(tweets)} 条推文")


@cli.command()
@click.option("--config", "-c", default=None, help="配置文件路径")
def init_config(config):
    """初始化配置文件"""
    dst = Path("config/settings.local.yaml")
    if dst.exists():
        click.echo(f"[跳过] {dst} 已存在")
        return

    src = Path("config/settings.yaml")
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    click.echo(f"[完成] 已创建 {dst}，请填入你的值")


def main():
    cli()


if __name__ == "__main__":
    main()
