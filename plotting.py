#plotting.py
import pyqtgraph as pg

def create_plot_widget(parent):
    """
    Initializes and returns a pyqtgraph PlotWidget with default labels and ranges.
    """
    plot_widget = pg.PlotWidget(parent)
    plot_widget.setLabel('left', 'AU_280nm')
    plot_widget.setLabel('bottom', 'Volume (ml)')
    plot_widget.setYRange(0, 0.2)
    plot_widget.setXRange(0, 20)
    return plot_widget

def update_plot(plot_widget, elapsed_time_data, eluate_volume_data,
        chan1_AU280_data, chan2_data, frac_mark_data,
        run_volume, max_y_value):
    """
    Updates the plot with new data and autoscales the Y-axis if needed.
    """
    plot_widget.clear()

    pen_chan1_AU280 = pg.mkPen(color='c', width=2)# Cyan
    pen_chan2 = pg.mkPen(color='y', width=2)# Yellow
    pen_frac_mark = pg.mkPen(color='m', width=2)# Magenta

    curve1 = plot_widget.plot(eluate_volume_data, chan1_AU280_data, pen=pen_chan1_AU280, name='AU_280')
    curve2 = plot_widget.plot(eluate_volume_data, chan2_data, pen=pen_chan2, name='Chan2')
    curve3 = plot_widget.plot(eluate_volume_data, frac_mark_data, pen=pen_frac_mark, name='Fraction')

    # Add legend if not already present
    if not plot_widget.plotItem.legend:
        legend = plot_widget.addLegend()
        legend.addItem(curve1, 'AU_280')
        legend.addItem(curve2, 'Chan2')
        legend.addItem(curve3, 'Fraction')

    # Set X-axis range
    plot_widget.setXRange(0, run_volume)

    # Autoscale Y-axis based on max AU_280 value
    if chan1_AU280_data:
        max_chan1 = max(chan1_AU280_data)
        new_max_y = max_chan1 * 1.1# Add 10% headroom
        if new_max_y > max_y_value:
            max_y_value = new_max_y
    plot_widget.setYRange(0, max_y_value)

    return max_y_value# Return updated max_y_value for tracking
