# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""看板 HTML 模板 — React 18 CDN + Tailwind + Chart.js.

用法:
    from spide.dashboard.template import DASHBOARD_TEMPLATE

    html = DASHBOARD_TEMPLATE.replace('{{JSON_DATA}}', json.dumps(data))
"""

DASHBOARD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN" class="antialiased">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SpideHarness Agent Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    background: linear-gradient(135deg, #0f181f 0%, #131f2a 50%, #0f181f 100%);
    margin: 0;
    color: #fafafa;
  }
  .scrollbar-thin::-webkit-scrollbar { width: 4px; }
  .scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
  .scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
  .scrollbar-thin::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .animate-row { animation: fadeIn 0.3s ease forwards; opacity: 0; }
</style>
</head>
<body>
<div id="root"></div>

<script>
// 注入看板数据
window.__DASHBOARD_DATA__ = {{JSON_DATA}};
</script>

<script>
(function() {
  'use strict';
  var h = React.createElement;
  var data = window.__DASHBOARD_DATA__;
  var d = data || {};

  // --- 常量 ---
  var PLATFORM_MAP = {
    weibo: {label:'微博', color:'#E6162D', bg:'rgba(230,22,45,0.2)', text:'text-red-400'},
    baidu: {label:'百度', color:'#4E6EF2', bg:'rgba(78,110,242,0.2)', text:'text-blue-400'},
    douyin: {label:'抖音', color:'#FE2C55', bg:'rgba(254,44,85,0.2)', text:'text-pink-400'},
    zhihu: {label:'知乎', color:'#0066FF', bg:'rgba(0,102,255,0.2)', text:'text-blue-300'},
    bilibili: {label:'B站', color:'#00A1D6', bg:'rgba(0,161,214,0.2)', text:'text-cyan-400'},
    kuaishou: {label:'快手', color:'#FF8C00', bg:'rgba(255,140,0,0.2)', text:'text-orange-400'},
    tieba: {label:'贴吧', color:'#4879BD', bg:'rgba(72,121,189,0.2)', text:'text-blue-400'},
    web_search: {label:'搜索', color:'#34D399', bg:'rgba(52,211,153,0.2)', text:'text-emerald-400'},
    custom: {label:'自定义', color:'#FBBF24', bg:'rgba(251,191,36,0.2)', text:'text-amber-400'},
  };

  var CATEGORY_COLORS = [
    'rgba(64,190,122,0.8)', 'rgba(126,212,166,0.8)',
    'rgba(78,110,242,0.7)', 'rgba(254,186,44,0.7)',
    'rgba(254,44,85,0.6)', 'rgba(160,160,160,0.4)',
    'rgba(167,139,250,0.7)', 'rgba(96,165,250,0.7)',
  ];

  // --- 工具函数 ---
  function fmt(n) {
    if (n == null) return '-';
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function shortTime(iso) {
    if (!iso) return '-';
    var d = new Date(iso);
    return d.getHours().toString().padStart(2,'0') + ':' +
           d.getMinutes().toString().padStart(2,'0');
  }

  // --- SVG 图标 ---
  function icon(pathData, size, color) {
    return h('svg', {
      width: size||16, height: size||16, viewBox:'0 0 24 24',
      fill:'none', stroke: color||'currentColor',
      strokeWidth:2, strokeLinecap:'round', strokeLinejoin:'round',
      className:'shrink-0'
    }, h('path', {d: pathData}));
  }

  var ICONS = {
    bar: 'M3 3v18h18M7 16V8m4 8V4m4 12V8m4 8V4',
    grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
    trend: 'M22 7l-8.5 8.5-5-5L2 17',
    flame: 'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z',
    spider: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
    globe: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z',
  };

  // --- 背景装饰 ---
  function BackgroundDecor() {
    return h('div', {className:'fixed inset-0 pointer-events-none overflow-hidden', 'aria-hidden':'true'},
      h('div', {className:'absolute -top-24 -right-24 w-96 h-96 rounded-full blur-3xl', style:{background:'rgba(64,190,122,0.08)'}}),
      h('div', {className:'absolute -bottom-24 -left-24 w-96 h-96 rounded-full blur-3xl', style:{background:'rgba(64,190,122,0.08)'}}),
      h('div', {className:'absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-3xl', style:{background:'rgba(64,190,122,0.04)'}})
    );
  }

  // --- Header ---
  function Header() {
    return h('header', {className:'h-14 px-6 flex items-center justify-between border-b shrink-0', style:{borderColor:'rgba(255,255,255,0.05)', background:'rgba(15,24,31,0.8)', backdropFilter:'blur(8px)'}},
      h('div', {className:'flex items-center gap-3'},
        icon(ICONS.spider, 24, '#40BE7A'),
        h('span', {className:'text-lg font-bold tracking-tight'}, 'SpideHarness Agent'),
        h('span', {className:'text-xs hidden sm:inline', style:{color:'#a0a0a0'}}, 'Dashboard')
      ),
      h('div', {className:'flex items-center gap-3'},
        h('span', {className:'text-[10px] px-2 py-0.5 rounded-full font-medium', style:{background:'rgba(64,190,122,0.15)', color:'#40BE7A', border:'1px solid rgba(64,190,122,0.3)'}}, 'v3.1.1 DEV'),
        d.latest_fetch ? h('span', {className:'text-xs font-mono', style:{color:'#a0a0a0'}}, shortTime(d.latest_fetch)) : null,
        h(Clock)
      )
    );
  }

  function Clock() {
    var dateRef = React.useRef(null);
    var timeRef = React.useRef(null);
    var WEEKDAYS = ['日','一','二','三','四','五','六'];
    React.useEffect(function() {
      function tick() {
        var now = new Date();
        if (dateRef.current) {
          dateRef.current.textContent = now.getFullYear() + '/' +
            (now.getMonth()+1).toString().padStart(2,'0') + '/' +
            now.getDate().toString().padStart(2,'0') + ' 周' + WEEKDAYS[now.getDay()];
        }
        if (timeRef.current) {
          timeRef.current.textContent = now.getHours().toString().padStart(2,'0') + ':' +
            now.getMinutes().toString().padStart(2,'0') + ':' +
            now.getSeconds().toString().padStart(2,'0');
        }
      }
      tick();
      var id = setInterval(tick, 1000);
      return function() { clearInterval(id); };
    }, []);
    return h('div', {className:'flex items-center gap-2 ml-2'},
      h('span', {ref: dateRef, className:'text-xs', style:{color:'#a0a0a0'}}),
      h('span', {ref: timeRef, className:'text-xs font-mono px-2 py-0.5 rounded', style:{color:'#7ED4A6', background:'rgba(126,212,166,0.1)'}})
    );
  }
    );
  }

  // --- 统计卡片 ---
  function StatCard(props) {
    return h('div', {className:'h-24 px-5 py-4 rounded-xl flex flex-col justify-between transition-all duration-200 hover:border-[#40BE7A]/30', style:{background:'rgba(26,37,48,0.6)', border:'1px solid rgba(255,255,255,0.1)', backdropFilter:'blur(24px)'}},
      h('div', {className:'flex items-center gap-2'},
        props.icon,
        h('span', {className:'text-xs font-medium', style:{color:'#a0a0a0'}}, props.label)
      ),
      h('div', {className:'text-2xl font-bold tabular-nums', style:{color:'#fafafa'}}, props.value)
    );
  }

  function StatsRow() {
    var s = d.stats_summary || {};
    return h('div', {className:'px-6 py-3 grid grid-cols-2 lg:grid-cols-4 gap-3 shrink-0'},
      h(StatCard, {label:'总话题数', value: fmt(s.total||0), icon: icon(ICONS.bar, 16, '#7ED4A6')}),
      h(StatCard, {label:'数据平台', value: String(s.platforms||0), icon: icon(ICONS.grid, 16, '#7ED4A6')}),
      h(StatCard, {label:'今日新增', value: '+' + fmt(s.today_count||0), icon: icon(ICONS.trend, 16, '#7ED4A6')}),
      h(StatCard, {label:'平均热度', value: fmt(s.avg_hot_value||0), icon: icon(ICONS.flame, 16, '#7ED4A6')})
    );
  }

  // --- 面板卡片容器 ---
  function Panel(props) {
    return h('div', {className:'rounded-xl flex flex-col min-h-0 overflow-hidden', style:{background:'rgba(26,37,48,0.6)', border:'1px solid rgba(255,255,255,0.1)', backdropFilter:'blur(24px)'}},
      h('div', {className:'px-4 py-3 flex items-center justify-between shrink-0', style:{borderBottom:'1px solid rgba(255,255,255,0.05)'}},
        h('span', {className:'text-sm font-semibold'}, props.title),
        props.subtitle ? h('span', {className:'text-[10px]', style:{color:'#a0a0a0'}}, props.subtitle) : null
      ),
      h('div', Object.assign({className:'flex-1 min-h-0 p-4'}, props.bodyProps || {}), props.children)
    );
  }

  // --- 平台分布图 ---
  function PlatformChart() {
    var ref = React.useRef(null);
    var chartRef = React.useRef(null);

    React.useEffect(function() {
      if (!ref.current || !d.platform_stats || d.platform_stats.length === 0) return;
      if (chartRef.current) chartRef.current.destroy();

      var ps = d.platform_stats;
      chartRef.current = new Chart(ref.current, {
        type: 'bar',
        data: {
          labels: ps.map(function(p) { return p.label; }),
          datasets: [{
            data: ps.map(function(p) { return p.count; }),
            backgroundColor: ps.map(function(p) { return (PLATFORM_MAP[p.source]||{}).color ? hexToRgba(PLATFORM_MAP[p.source].color, 0.6) : 'rgba(64,190,122,0.6)'; }),
            borderColor: ps.map(function(p) { return (PLATFORM_MAP[p.source]||{}).color || '#40BE7A'; }),
            borderWidth: 1,
            borderRadius: 4,
            barPercentage: 0.7,
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: {display:false} },
          scales: {
            x: { grid:{color:'rgba(255,255,255,0.05)'}, ticks:{color:'#a0a0a0', font:{size:10}}, border:{display:false} },
            y: { grid:{display:false}, ticks:{color:'#fafafa', font:{size:12, weight:'500'}}, border:{display:false} }
          },
          animation: {duration:800, easing:'easeOutQuart'}
        }
      });
      return function() { if (chartRef.current) chartRef.current.destroy(); };
    }, []);

    return h(Panel, {title:'平台分布', subtitle: (d.platform_stats||[]).length + ' 个平台'},
      h('div', {style:{position:'relative', width:'100%', height:'100%'}},
        h('canvas', {ref: ref})
      )
    );
  }

  function hexToRgba(hex, alpha) {
    if (!hex) return 'rgba(64,190,122,' + alpha + ')';
    var r = parseInt(hex.slice(1,3), 16);
    var g = parseInt(hex.slice(3,5), 16);
    var b = parseInt(hex.slice(5,7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  // --- 分类饼图 ---
  function CategoryPie() {
    var ref = React.useRef(null);
    var chartRef = React.useRef(null);

    React.useEffect(function() {
      if (!ref.current || !d.category_stats || d.category_stats.length === 0) return;
      if (chartRef.current) chartRef.current.destroy();

      var cs = d.category_stats;
      var total = cs.reduce(function(a,c) { return a + c.count; }, 0);
      chartRef.current = new Chart(ref.current, {
        type: 'doughnut',
        data: {
          labels: cs.map(function(c) { return c.category; }),
          datasets: [{
            data: cs.map(function(c) { return c.count; }),
            backgroundColor: CATEGORY_COLORS.slice(0, cs.length),
            borderColor: '#1a2530',
            borderWidth: 2,
            hoverOffset: 6,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '60%',
          plugins: {
            legend: {position:'bottom', labels:{color:'#a0a0a0', font:{size:10}, padding:8, usePointStyle:true, pointStyleWidth:8}},
          },
          animation: {animateRotate:true, duration:1000}
        },
        plugins: [{
          id: 'centerText',
          beforeDraw: function(chart) {
            var ctx = chart.ctx;
            var cx = (chart.chartArea.left + chart.chartArea.right) / 2;
            var cy = (chart.chartArea.top + chart.chartArea.bottom) / 2;
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.font = 'bold 18px Inter, system-ui';
            ctx.fillStyle = '#fafafa';
            ctx.fillText(String(cs.length), cx, cy - 6);
            ctx.font = '10px Inter, system-ui';
            ctx.fillStyle = '#a0a0a0';
            ctx.fillText('个分类', cx, cy + 10);
            ctx.restore();
          }
        }]
      });
      return function() { if (chartRef.current) chartRef.current.destroy(); };
    }, []);

    return h(Panel, {title:'分类占比'},
      h('div', {style:{position:'relative', width:'100%', height:'100%'}},
        h('canvas', {ref: ref})
      )
    );
  }

  // --- 排行榜 ---
  function RankingTable() {
    var topics = d.top_topics || [];
    if (topics.length === 0) {
      return h(Panel, {title:'热搜排行榜', subtitle:'Top 20'},
        h('div', {className:'flex items-center justify-center h-full', style:{color:'#a0a0a0'}},
          h('div', {className:'text-center'},
            h('p', {className:'text-sm'}, '暂无数据'),
            h('p', {className:'text-xs mt-1'}, '运行 spide crawl 采集热搜')
          )
        )
      );
    }

    var rows = topics.map(function(t, i) {
      var pm = PLATFORM_MAP[t.source] || {label:t.source, bg:'rgba(64,190,122,0.2)', text:'text-emerald-400', color:'#40BE7A'};
      var rankStyle = i === 0 ? {background:'rgba(245,158,11,0.15)', color:'#fbbf24'}
                     : i === 1 ? {background:'rgba(156,163,175,0.15)', color:'#d1d5db'}
                     : i === 2 ? {background:'rgba(251,146,60,0.15)', color:'#fb923c'}
                     : {background:'rgba(255,255,255,0.05)', color:'#a0a0a0'};

      return h('div', {
        key: i,
        className: 'grid grid-cols-[36px_1fr_72px_80px] gap-2 px-4 py-2.5 items-center animate-row transition-colors duration-150 hover:bg-white/5',
        style: {borderBottom:'1px solid rgba(255,255,255,0.05)', animationDelay: (i*30)+'ms'}
      },
        h('div', {className:'w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0', style:rankStyle}, t.rank),
        t.url ? h('a', {href:t.url, target:'_blank', rel:'noopener noreferrer', className:'text-sm truncate hover:underline', style:{color:'#fafafa'}, title:t.title}, t.title)
               : h('div', {className:'text-sm truncate', style:{color:'#fafafa'}, title:t.title}, t.title),
        h('div', {className:'flex items-center gap-1.5'},
          h('span', {className:'w-1.5 h-1.5 rounded-full shrink-0', style:{background:pm.color}}),
          h('span', {className:'text-[10px] font-medium px-1.5 py-0.5 rounded-full', style:{background:pm.bg, color:pm.color}}, pm.label)
        ),
        h('div', {className:'text-sm font-mono tabular-nums text-right', style:{color:'#fafafa'}}, fmt(t.hot_value))
      );
    });

    return h(Panel, {title:'热搜排行榜', subtitle:'Top ' + topics.length, bodyProps:{className:'flex-1 min-h-0 px-0 py-0 flex flex-col'}},
      h('div', {className:'grid grid-cols-[36px_1fr_72px_80px] gap-2 px-4 py-2 text-[10px] font-medium shrink-0', style:{color:'#a0a0a0', borderBottom:'1px solid rgba(255,255,255,0.05)', background:'rgba(15,24,31,0.5)'}},
        h('span', null, '排名'), h('span', null, '标题'), h('span', null, '来源'), h('span', {className:'text-right'}, '热度')
      ),
      h('div', {className:'flex-1 min-h-0 overflow-y-auto scrollbar-thin'}, rows)
    );
  }

  // --- 平台 Top3 卡片 ---
  function PlatformTop3Card(props) {
    var source = props.source;
    var items = props.items || [];
    var pm = PLATFORM_MAP[source] || {label:source, color:'#40BE7A'};

    var entries = items.map(function(item, i) {
      return h('div', {key:i, className:'px-4 py-2 flex items-start gap-2 transition-colors hover:bg-white/5', style:{borderBottom: i < items.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'}},
        h('span', {className:'text-xs font-mono w-4 shrink-0 mt-0.5', style:{color:'#a0a0a0'}}, item.rank + '.'),
        h('div', {className:'flex-1 min-w-0'},
          item.url ? h('a', {href:item.url, target:'_blank', rel:'noopener noreferrer', className:'text-xs truncate hover:underline', style:{color:'#fafafa'}}, item.title)
                    : h('div', {className:'text-xs truncate', style:{color:'#fafafa'}}, item.title),
          h('div', {className:'text-[10px] font-mono mt-0.5', style:{color:'#a0a0a0'}}, fmt(item.hot_value))
        )
      );
    });

    return h('div', {className:'rounded-xl overflow-hidden', style:{background:'rgba(26,37,48,0.6)', border:'1px solid rgba(255,255,255,0.1)', borderLeft:'3px solid ' + pm.color}},
      h('div', {className:'px-4 py-2.5 flex items-center gap-2', style:{borderBottom:'1px solid rgba(255,255,255,0.05)'}},
        h('span', {className:'w-2 h-2 rounded-full', style:{background:pm.color}}),
        h('span', {className:'text-sm font-semibold'}, pm.label + ' Top ' + items.length)
      ),
      entries.length > 0 ? entries : h('div', {className:'px-4 py-3 text-xs text-center', style:{color:'#a0a0a0'}}, '暂无数据')
    );
  }

  function PlatformTop3Group() {
    var ranks = d.platform_ranks || {};
    var cards = Object.keys(ranks).map(function(source) {
      return h(PlatformTop3Card, {key:source, source:source, items:ranks[source]});
    });
    return h('div', {className:'flex flex-col gap-3'}, cards);
  }

  // --- 空状态 ---
  function EmptyState() {
    return h('div', {className:'flex-1 flex items-center justify-center'},
      h('div', {className:'text-center'},
        icon(ICONS.globe, 48, '#40BE7A'),
        h('h2', {className:'text-lg font-semibold mt-4'}, '暂无看板数据'),
        h('p', {className:'text-sm mt-2', style:{color:'#a0a0a0'}}, '运行以下命令采集数据：'),
        h('code', {className:'text-xs mt-3 inline-block px-3 py-1.5 rounded-lg', style:{background:'rgba(64,190,122,0.15)', color:'#40BE7A'}}, 'spide crawl --all')
      )
    );
  }

  // --- Footer ---
  function Footer() {
    return h('footer', {className:'h-8 px-6 flex items-center justify-center shrink-0', style:{borderTop:'1px solid rgba(255,255,255,0.05)'}},
      h('span', {className:'text-[10px]', style:{color:'#a0a0a0'}}, 'Powered by SpideHarness Agent v3.1.1 DEV | IoTchange')
    );
  }

  // --- App ---
  function App() {
    var hasData = d.total_count > 0;

    return h('div', {className:'h-screen w-screen overflow-hidden flex flex-col relative'},
      h(BackgroundDecor),
      h(Header),
      hasData ? h(StatsRow) : null,
      hasData
        ? h('div', {className:'flex-1 min-h-0 px-6 pb-3 grid grid-cols-12 gap-3'},
            h('div', {className:'col-span-4 hidden lg:flex flex-col gap-3 min-h-0'},
              h('div', {className:'flex-[3] min-h-0'}, h(PlatformChart)),
              h('div', {className:'flex-[2] min-h-0'}, h(CategoryPie))
            ),
            h('div', {className:'col-span-12 lg:col-span-5 min-h-0'}, h(RankingTable)),
            h('div', {className:'col-span-3 hidden lg:block min-h-0 overflow-y-auto scrollbar-thin'}, h(PlatformTop3Group))
          )
        : h(EmptyState),
      h(Footer)
    );
  }

  // --- 渲染 ---
  Chart.defaults.color = '#a0a0a0';
  Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(26,37,48,0.95)';
  Chart.defaults.plugins.tooltip.titleColor = '#fafafa';
  Chart.defaults.plugins.tooltip.bodyColor = '#a0a0a0';
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.1)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.plugins.tooltip.padding = 10;

  var root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(h(App));
})();
</script>
</body>
</html>
"""
