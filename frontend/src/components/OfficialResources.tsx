const RESOURCES = [
  ["全国雷达拼图", "对照当前降水回波", "https://www.nmc.cn/publish/radar/chinaall.html"],
  ["近 1 小时降水", "核对降水实况", "https://www.nmc.cn/publish/observations/hourly-precipitation.html"],
  ["24 小时降水预报", "查看全国预报落区", "https://www.nmc.cn/publish/precipitation/1-day.html"],
  ["FY-4B 卫星云图", "查看云系演变", "https://www.nmc.cn/publish/satellite/fy4b-visible.htm"],
  ["中央气象台台风网", "查看台风路径与产品", "http://typhoon.nmc.cn/"],
  ["CMA 预警地图", "查看官方预警空间展示", "https://weather.cma.cn/web/alarm/map.html"],
];

export function OfficialResources() {
  return (
    <section className="card official-resources">
      <span className="eyebrow">OFFICIAL CONTEXT</span><h2>官方辅助信息</h2>
      <p className="section-description">打开官方产品查看实况、落区和路径；这些外部页面未作为本看板的结构化实时数据接入。</p>
      <div className="official-resource-grid">{RESOURCES.map(([title, description, url]) => (
        <a href={url} target="_blank" rel="noreferrer" key={url}><strong>{title} ↗</strong><span className="meta">{description}</span></a>
      ))}</div>
    </section>
  );
}
