# AlumFrame — FreeCAD 铝型材框架生成器

FreeCAD 工作台插件，用于快速创建参数化铝型材方管框架，自动生成 BOM（含每根型材打孔/攻丝坐标）和尺寸标注。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 参数化框架生成 | 改 Parameters 参数表 → 几何/标注/BOM 实时联动 |
| 自动 BOM | 按型材规格汇总，含每根型材打孔坐标说明 |
| 尺寸标注 | `Measure::MeasureLength`，含柱距/净空/总外形 |
| 编辑已有框架 | 选中 Frame → Edit Frame，面板预填当前参数 |
| CSV 导出 | BOM 可导出 CSV，方便采购 |

---

## 支持的型材规格

| 规格 | 截面 | 十字通孔 | 攻丝 |
|------|------|---------|------|
| 20x20 | 方管 | M5 | M6 |
| 30x30 | 方管 | M6 | M8 |
| 40x40 | 方管 | M8 | M10 |
| 60x60 | 方管 | M10 | M12 |

### 2D DXF 资源（MISUMI/米思米）

项目集成米思米 T-slot 铝型材 2D 截面（`profiles/dxf/`），支持以下规格：

| DXF 文件 | 截面尺寸 | 类型 |
|----------|---------|------|
| `nfs5-2020.dxf` | 20x20 方管 | 标准 |
| `nfs5-2040.dxf` | 20x40 矩形 | 标准 |
| `nfs5-2060.dxf` | 20x60 矩形 | 标准 |
| `nfs5-2080.dxf` | 20x80 矩形 | 标准 |
| `nfs5-4040.dxf` | 40x40 方管 | 标准 |
| `LCF8-3030.dxf` | 30x30 方管 | T-slot |
| `LCF8-4040.dxf` | 40x40 方管 | T-slot |
| `nefs8-4040.dxf` | 40x40 方管 | T-slot |
| `nefs8-4080.dxf` | 40x80 矩形 | T-slot |
| `hfs8-4040.dxf` | 40x40 方管 | T-slot |

> DXF 文件来源：米思米（MISUMI）铝型材 CAD 资源库。在 `profiles/dxf/` 目录下，解压后自动加载。

---

## 框架几何规则

```
坐标系原点：框架底面中心 (0, 0, 0)
Z 轴：竖直向上
框架外边界：X = ±L/2,  Y = ±W/2,  Z = [0, H]
```

- Z 立柱位于 4 个外角，柱外角与框架外角对齐
- X 横梁两端贴合 Z 立柱内侧面（梁长 = L - 2×截面宽度）
- Y 纵梁两端贴合 Z 立柱内侧面（梁长 = W - 2×截面宽度）
- 截面中心与立柱截面中心齐平（梁 Z 基线 = 0，不居中于截面高度）

---

## 打孔情况

### X-横梁 / Y-纵梁（水平梁）

**两端攻丝**：M6 螺纹孔，每根梁 2 处（低端面 + 高端面），深度 = 1.5×直径：
- X 梁：端点 (x=0或L, y=profile/2, z=profile/2)
- Y 梁：端点 (x=profile/2, y=0或W, z=profile/2)

### Z 立柱（竖柱）

**每层 M5 十字通孔**：穿过型材，梁通过并用 M5 螺栓固定。
**顶底两端 M6 攻丝**：底部固定底板，顶部固定顶板。

---

## 示例：z_layers=2 时的 BOM 打孔说明

```
X-横梁：
每根2处攻丝（沿梁轴），截面中心
  端1: M6距端面0mm 深9mm  (x=0, y=10, z=10)
  端2: M6距端面560mm 深9mm  (x=560, y=10, z=10)

Y-纵梁：
每根2处攻丝（沿梁轴），截面中心
  端1: M6距端面0mm 深9mm  (x=10, y=0, z=10)
  端2: M6距端面360mm 深9mm  (x=10, y=360, z=10)

Z-立柱：
Z柱 3层：每层M5十字通孔，顶底M6攻丝
  底部: M5十字通孔 + M6攻丝 距底面0mm/深9mm  (x=10, y=10, z=0)
  第2层: M5十字通孔  (x=10, y=10, z=240)
  顶部: M5十字通孔 + M6攻丝 距底面480mm/深9mm  (x=10, y=10, z=480)
```

---

## 参数表（Parameters）

在 FreeCAD 中，每个框架生成一个 `Parameters` 电子表格，作为**单一数据源**：

| 单元格 | 含义 | 示例 |
|--------|------|------|
| B1 | 型材规格 | 20x20 |
| B2 | 型材宽度 (mm) | 20 |
| B3 | 外形长度 X (mm) | 600 |
| B4 | 外形宽度 Y (mm) | 400 |
| B5 | 外形高度 Z (mm) | 500 |
| B6 | Z 层数 | 1 |
| B7 | 材料 | Aluminum 6061 |

> 直接修改 B3（长度）等单元格 → 几何/标注实时更新，无需重新生成。
> 修改 Frame 组属性面板也会同步更新参数表（双向通道）。

---

## 安装

```bash
# 1. 将仓库克隆到 FreeCAD 插件目录
git clone git@github.com:gdbdzgd/AulmFrame-.git ~/.FreeCAD/Mod/AlumFrame

# 或者创建软链接（开发模式）
ln -s /path/to/repo ~/.FreeCAD/Mod/AlumFrame
```

重启 FreeCAD 后，工具栏出现 **New Frame** 和 **Edit Frame** 按钮。

---

## 使用方法

### 新建框架

1. 打开 FreeCAD，切换到 **AlumFrame** 工作台
2. 点击 **New Frame** 按钮，输入参数，点击 OK
3. 框架几何 + BOM + 标注自动生成

### 编辑已有框架

1. 选中任意框架零件（梁或立柱均可）
2. 点击 **Edit Frame** 按钮（或菜单 AlumFrame → Edit）
3. 面板预填当前参数，修改后点击 OK 即原地重建

### 导出 BOM CSV

```python
from AulmFrame.bom import export_bom_csv
export_bom_csv(beams, '/tmp/bom.csv', material='Aluminum 6061',
               hole_spec={'beam_cross': 'M5', 'post_tap': 'M6'},
               profile_size=20)
```

---

## 单元测试

无需 FreeCAD 即可运行：

```bash
python3 -m unittest discover tests -v
```

测试内容：锚点位置、梁间距、梁长度、Z 层间距、全型材验证、BOM 打孔坐标。

---

## 目录结构

```
AulmFrame/
├── __init__.py           # make_frame() 入口
├── config.py             # 型材规格、打孔规格、对象名常量
├── position_calculator.py # 锚点/梁长/间距公式
├── beam_factory.py       # 梁几何体创建（Part::Box / Part::Feature）
├── frame_builder.py      # 框架编排（组装梁+立柱+阵列+参数表）
├── bom.py                # BOM 电子表格 + 打孔说明 + CSV 导出
├── measurements.py       # 尺寸标注（Measure::MeasureLength）
├── Gui.py                # 任务面板（新建/编辑）
├── InitGui.py            # 工作台入口
├── tests/
│   └── test_position_calculator.py  # 单元测试
└── README.md
```

---

## 技术限制

- BOM 为静态文本，直接修改参数表后需通过面板"重建"刷新（走面板编辑时自动同步）
- 圆管/矩形管型材暂时移除（代码保留），当前仅支持方管
- 不支持部分立柱（4 立柱/整数层为固定拓扑）
