/** @odoo-module */


import { CharField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { loadCSS,loadJS } from "@web/core/assets";
import { qweb } from 'web.core';
import core from 'web.core';
import session from 'web.session';

const { useEffect, useRef, xml, onWillUpdateProps,onMounted,onWillStart,Component} = owl;

  export class KsGraphViewOwl extends Component{
  setup() {
        super.setup();
        const self = this;
        loadJS('ks_woocommerce/static/lib/js/Chart.js');
//        loadJS('/ks_shopify/static/lib/js/chartjs-plugin-datalabels.js');
//        const canvasRef = useRef("canvas");

        useEffect(() => {
            this._Ks_render();
        });


    }

        _ks_line_chart(ev){
//        $(ev.target.parentElement.parentElement.parentElement.parentElement).find(".ks_header_part").text("Line Chart")
            this.render_Linechart();
        }

        _ks_bar_chart(ev){
//        $(ev.target.parentElement.parentElement.parentElement.parentElement).find(".ks_header_part").text("Bar Chart")
            this.render_Barchart();
        }
//        _ks_pie_chart(){
//            this.render_Piechart();
//        }

        _Ks_render() {
            if(this.props.record.data.ks_chart_data){
                    this.render_Barchart();
            }
            else{
                this.render_Linechart();
            }
        }

        render_Linechart(){
        var header = "Line Chart"
         let header_new= document.getElementsByClassName("ks_header_part");
            $(header_new).text(header);
            var canvas = '<canvas id="canvas" style="width: 650px; height: 300px"></canvas>'
            let  c = document.getElementsByClassName("ks_chart_container");
             if(document.querySelector("#canvas")==null){
              $(c).append($(canvas))
             }else{
             document.querySelector("#canvas").remove()
              $(c).append($(canvas))
             }
            let ctx = $(c).find('#canvas').get(0).getContext('2d');
            var chart_data = JSON.parse(this.props.record.data.ks_chart_data)
            var myChart = new Chart(ctx, {
                type: 'line',
                data: chart_data,
                options: {

                }
            });
            this.ks_chart_color(myChart, 'line')
        }

        ks_chart_color(ksMyChart, ksChartType){
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
        }

        render_Barchart(){
            var header = "Bar Chart"
            let header_new= document.getElementsByClassName("ks_header_part");
            $(header_new).text(header);
            var canvas = '<canvas id="canvas" style="width: 850px; height: 500px"></canvas>'
            let  c = document.getElementsByClassName("ks_chart_container");
            if(document.querySelector("#canvas")==null){
                    $(c).append($(canvas))
                    }else{
                    document.querySelector("#canvas").remove()
                     $(c).append($(canvas))
                     }
            let ctx = $(c).find('#canvas').get(0).getContext('2d');
            var chart_data = JSON.parse(this.props.record.data.ks_chart_data)
            var myChart = new Chart(ctx, {
                type: 'bar',
                data: chart_data,
                options: {
                }
            });
            this.ks_chart_color(myChart, 'bar')
        }

//        render_Piechart(){
//        var $chartContainer = $(qweb.render('Graph_template'));
//        $(this.input.el.parentElement).append($chartContainer);
//        $(this.input.el.parentElement).find('.ks_chart_container').empty()
//
//            var canvas = '<canvas id="canvas" style="width: 850px; height: 500px"></canvas>'
//            $(this.input.el.parentElement).find('.ks_chart_container').append($(canvas))
//
//            var header = "Pie Chart"
//            $(this.input.el.parentElement).find('.ks_header').find('.ks_header_part').text(header);
//
//            var ctx = $(this.input.el.parentElement).find('#canvas').get(0).getContext('2d');
//            var chart_data = JSON.parse(this.props.record.data.ks_chart_data_pie)
//            var myChart = new Chart(ctx, {
//                type: 'pie',
//                data: chart_data,
//                options: {
//                }
//            });
//            this.ks_chart_color(myChart, 'pie')
//        }
    }

   registry.category("fields").add('ks_graph_owl', KsGraphViewOwl);
   KsGraphViewOwl.template = "Graph_template";
    return {
        KsGraphViewOwl: KsGraphViewOwl,
    }
