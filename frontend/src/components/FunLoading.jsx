import React, { useState, useEffect } from 'react';

const FUN_QUOTES = [
    "正在给 DeepSeek 喂电子咖啡...",
    "正在翻阅互联网的每一个角落 (嘘...)",
    "AI 正在进行激烈的哲学思考...",
    "试图分辨 '土豆' 和 '马铃薯' 的区别...",
    "正在与 Redis 进行数据握手...",
    "为了真相，跑断了虚拟的腿...",
    "正在召唤神龙进行校验...",
    "加载中... 请不要关闭浏览器，也不要闭眼...",
    "正在从 1000 万个网页中寻找证据...",
    "事实守护者正在穿梭时空..."
];

const EMOJIS = ['🤖', '🕵️‍♂️', '🦉', '🧠', '🔍'];

export default function FunLoading({ progressText }) {
    const [quoteIndex, setQuoteIndex] = useState(0);
    const [emojiIndex, setEmojiIndex] = useState(0);

    useEffect(() => {
        // 每 2.5 秒换一句话
        const quoteTimer = setInterval(() => {
            setQuoteIndex(prev => (prev + 1) % FUN_QUOTES.length);
        }, 2500);

        // 每 0.8 秒换一个表情
        const emojiTimer = setInterval(() => {
            setEmojiIndex(prev => (prev + 1) % EMOJIS.length);
        }, 800);

        return () => {
            clearInterval(quoteTimer);
            clearInterval(emojiTimer);
        };
    }, []);

    return (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-50 flex flex-col items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full text-center border-4 border-brand-100 transform transition-all duration-500 hover:scale-105">
                
                {/* 动画区域 */}
                <div className="relative h-32 mb-6 flex items-center justify-center">
                    {/* 背景装饰光环 */}
                    <div className="absolute w-24 h-24 bg-blue-100 rounded-full animate-ping opacity-20"></div>
                    <div className="absolute w-32 h-32 bg-purple-100 rounded-full animate-ping opacity-10 animation-delay-500"></div>
                    
                    {/* 核心表情 */}
                    <div className="text-8xl animate-bounce filter drop-shadow-lg transform transition-all duration-300">
                        {EMOJIS[emojiIndex]}
                    </div>
                </div>

                {/* 核心进度提示 */}
                <h3 className="text-xl font-bold text-slate-800 mb-2 min-h-[1.75rem]">
                    {progressText}
                </h3>

                {/* 进度条 */}
                <div className="w-full bg-slate-100 rounded-full h-2 mb-6 overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-brand-400 via-purple-400 to-brand-600 animate-progress w-full origin-left"></div>
                </div>

                {/* 趣味语录 */}
                <div className="h-8 flex items-center justify-center">
                    <p className="text-slate-500 text-sm italic font-medium animate-fade-in-up key={quoteIndex}">
                        "{FUN_QUOTES[quoteIndex]}"
                    </p>
                </div>
            </div>
            
            {/* 底部小提示 */}
            <p className="text-white/80 mt-8 text-sm font-light tracking-wide">
                FactGuardian · 使得事实更清晰
            </p>
        </div>
    );
}

// 在 index.css 中补充动画所需的类（如果 Tailwind 默认不够用）
// animate-progress 需要在 tailwind.config.js 中配置，这里先用简单的模拟
