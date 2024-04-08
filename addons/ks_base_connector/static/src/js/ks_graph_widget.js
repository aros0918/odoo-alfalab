odoo.define('ks_woocommerce.KsGraphView', function (require) {
    "use strict";
    var AbstractField = require('web.AbstractField');
    var ks_field_registry = require('web.field_registry');
    var ajax = require('web.ajax');

    var KsGraphView = AbstractField.extend({
        jsLibs: [
           '/web/static/lib/Chart/Chart.js',
        ],
        resetOnAnyFieldChange: true,
        template: 'Graph_template',
        xmlDependencies: [
            '/ks_woocommerce/static/src/xml/ks_graph_template.xml',
        ],
        events: {
            'click #ks_line_chart': '_ks_line_chart',
            'click #ks_bar_chart': '_ks_bar_chart',
            'click #ks_pie_chart': '_ks_pie_chart'
        },
        init: function (parent, value) {
            var self = this;
            this._super.apply(this,arguments);
        },

        _ks_line_chart: function(){
            this.render_Linechart();
        },

        _ks_bar_chart: function(){
            this.render_Barchart();
        },
        _ks_pie_chart: function(){
            this.render_Piechart();
        },

        _render: function () {
            this._super.apply(this, arguments);
            if(this.recordData.ks_chart_data){
                    this.render_Barchart();
            }
            else{
                this.render_Piechart();
            }
        },

        render_Linechart:function(){
            this.$el.find('.ks_chart_container').empty()

            var canvas = '<canvas id="canvas" style="width: 850px; height: 400px"></canvas>'
            this.$el.find('.ks_chart_container').append($(canvas))

            var header = "Line Chart"
            this.$el.find('.ks_header').find('.ks_header_part').text(header);

            var ctx = this.$el.find('#canvas').get(0).getContext('2d');
            var chart_data = JSON.parse(this.recordData.ks_chart_data)
            var myChart = new Chart(ctx, {
                type: 'line',
                data: chart_data,
                options: {

                }
            });
            this.ks_chart_color(myChart, 'line')
        },

        ks_chart_color: function(ksMyChart, ksChartType){
            var chartColors = [];
            var datasets = ksMyChart.config.data.datasets;
            var setsCount = datasets.length;
            var color_set = ['#F04F65', '#f69032', '#fdc233', '#53cfce', '#36a2ec', '#8a79fd', '#b1b5be', '#1c425c', '#8c2620', '#71ecef', '#0b4295', '#f2e6ce', '#1379e7']
            for (var i = 0, counter = 0; i < setsCount; i++, counter++) {
                if (counter >= color_set.length) counter = 0; // reset back to the beginning
                chartColors.push(color_set[counter]);
            }
            for (var i = 0; i < datasets.length; i++) {
                switch (ksChartType) {
                    case "line":
                        datasets[i].borderColor = chartColors[i];
                        datasets[i].backgroundColor = "rgba(255,255,255,0)";
                        break;
                    case "bar":
                        datasets[i].backgroundColor = chartColors[i];
                        datasets[i].borderColor = "rgba(255,255,255,0)";
                        break;
                    case "pie":
                        datasets[i].backgroundColor = chartColors[i];
                        datasets[i].borderColor = "rgba(255,255,255,0)";
                        break;
                }
            }
            ksMyChart.update();
        },

        render_Barchart:function(){
            this.$el.find('.ks_chart_container').empty()

            var canvas = '<canvas id="canvas" style="width: 850px; height: 500px"></canvas>'
            this.$el.find('.ks_chart_container').append($(canvas))

            var header = "Bar Chart"
            this.$el.find('.ks_header').find('.ks_header_part').text(header);

            var ctx = this.$el.find('#canvas').get(0).getContext('2d');
            var chart_data = JSON.parse(this.recordData.ks_chart_data)
            var myChart = new Chart(ctx, {
                type: 'bar',
                data: chart_data,
                options: {
                }
            });
            this.ks_chart_color(myChart, 'bar')
        },
        render_Piechart:function(){
            this.$el.find('.ks_chart_container').empty()

            var canvas = '<canvas id="canvas" style="width: 850px; height: 500px"></canvas>'
            this.$el.find('.ks_chart_container').append($(canvas))

            var header = "Pie Chart"
            this.$el.find('.ks_header').find('.ks_header_part').text(header);

            var ctx = this.$el.find('#canvas').get(0).getContext('2d');
            var chart_data = JSON.parse(this.recordData.ks_chart_data_pie)
            var myChart = new Chart(ctx, {
                type: 'pie',
                data: chart_data,
                options: {
                }
            });
            this.ks_chart_color(myChart, 'pie')
        },
    });

    ks_field_registry.add('ks_graph', KsGraphView);
    return KsGraphView;

});