"""
可视化模块后端代码
"""
import pyecharts.options as opts
from pyecharts.charts import TreeMap, Line, Grid


def extract(target, indicator, calc_results):
    target['value'] = round(calc_results[indicator], 2)
    for index in range(len(calc_results['children'])):
        element = calc_results['children'][index]
        child = {'name': element['name'], 'children': []}
        target['children'].append(child)

        if len(element['children']) == 0:
            child['value'] = round(element.get(indicator, None), 2)
            return
        else:
            extract(child, indicator, element)


def to_treemap(data, proj, version):
    complexity = {'name': f'{proj}-{version}', 'children': []}
    extract(complexity, 'complexity', data)
    maintainability = {'name': f'{proj}-{version}', 'children': []}
    extract(maintainability, 'maintainability', data)
    testability = {'name': f'{proj}-{version}', 'children': []}
    extract(testability, 'testability', data)
    readability = {'name': f'{proj}-{version}', 'children': []}
    extract(readability, 'readability', data)
    reusability = {'name': f'{proj}-{version}', 'children': []}
    extract(reusability, 'reusability', data)
    inheritance = {'name': f'{proj}-{version}', 'children': []}
    extract(inheritance, 'inheritance', data)

    treemap = TreeMap()
    for indicator in ['complexity', 'maintainability', 'testability', 'readability', 'reusability', 'inheritance']:
        treemap = treemap.add(
            series_name=indicator,
            data=[locals()[indicator]],
            leaf_depth=2,
            roam=False,
            label_opts=opts.LabelOpts(position='inside')
        )

    treemap = (
        treemap.set_global_opts(
            tooltip_opts=opts.TooltipOpts(formatter='{b}<br/>{a}: {c}'),
            toolbox_opts=opts.ToolboxOpts(
                feature=opts.ToolBoxFeatureOpts(
                    magic_type=opts.ToolBoxFeatureMagicTypeOpts(is_show=False),
                    data_zoom=opts.ToolBoxFeatureDataZoomOpts(is_show=False),
                    brush=opts.ToolBoxFeatureBrushOpts(type_='clear')
                )),
            legend_opts=opts.LegendOpts(
                is_show=True, selected_mode='single', pos_top='7%', orient='horizontal', padding=0),
            title_opts=opts.TitleOpts(title=f'Code Quality Treemap of {proj}-{version}', pos_left='center')
        )
    )
    grid = Grid()
    grid.add(treemap, grid_opts=opts.GridOpts(pos_top='100%'))
    return grid


def to_linechart(data, proj):
    versions = [version['version_name'] for version in data]
    linechart = Line().add_xaxis(xaxis_data=versions)
    for indicator in ['complexity', 'maintainability', 'testability', 'readability', 'reusability', 'inheritance']:
        linechart = linechart.add_yaxis(
            series_name=indicator,
            y_axis=[round(version[indicator], 2) for version in data],
            is_smooth=True,
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=2),
        )

    linechart = (
        linechart.set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
            xaxis_opts=opts.AxisOpts(boundary_gap=False),
            yaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(formatter="{value}"),
                splitline_opts=opts.SplitLineOpts(is_show=True),
            ),
            toolbox_opts=opts.ToolboxOpts(
                feature=opts.ToolBoxFeatureOpts(
                    magic_type=opts.ToolBoxFeatureMagicTypeOpts(is_show=False),
                    data_zoom=opts.ToolBoxFeatureDataZoomOpts(is_show=False),
                    brush=opts.ToolBoxFeatureBrushOpts(type_='clear')
                )),
            legend_opts=opts.LegendOpts(
                is_show=True, pos_top='middle', pos_left='1%', orient='vertical', padding=0),
            datazoom_opts=opts.DataZoomOpts(type_='slider', range_start=0, range_end=100),
            title_opts=opts.TitleOpts(title=f'Code Quality Linechart of {proj}', pos_left='center')
        )
    )
    grid = Grid()
    grid.add(linechart, grid_opts=opts.GridOpts(pos_left='150'))
    return grid
