<template>
    <span class="small-scatter">
        <vue-plotly :data="data" :layout="layout" :options="options"/>
    </span>
</template>

<script>
    import VuePlotly from '@statnett/vue-plotly'

    export default {
        name: "ScatterPlot",
        props: {
          scatter_x: {
            type: Object,
            required: true
          },
          scatter_y: {
            type: Object,
            required: true
          }
        },
        methods:{
        },
        components: {
            VuePlotly,
        },
        computed: {

            values_y(){
                var y;
                var title_y;
                if  (!this.scatter_y.value.every(function(v) { return v === null})) {
                    y = this.scatter_y.value;
                    title_y = "value"
                }
                else if (!this.scatter_y.mean.every(function(v) { return v === null})){
                    y = this.scatter_y.mean;
                    title_y = "mean"
                }
                else if (!this.scatter_y.median.every(function(v) { return v === null})){
                    y = this.scatter_y.median;
                    title_y = "median"
                }
                return {y, title_y};
            },
            values_x(){
              var x;
              var title_x;
              if  (!this.scatter_x.value.every(function(v) { return v === null})) {
                x = this.scatter_x.value;
                title_x = "value"
              }
              else if (!this.scatter_x.mean.every(function(v) { return v === null})){
                x = this.scatter_x.mean;
                title_x = "mean"
              }
              else if (!this.scatter_x.median.every(function(v) { return v === null})){
                x = this.scatter_x.median;
                title_x = "median"
              }
              return {x, title_x};
            },
            errors_y(){
                var y;
                var title_y;
                if  (!this.scatter_y.sd.every(function(v) { return v === null})) {
                    y = this.scatter_y.sd;
                    title_y = "sd"
                }
                else if (!this.scatter_y.se.every(function(v) { return v === null})){
                    y = this.scatter_y.se;
                    title_y = "se"
                }
                else if (!this.scatter_y.cv.every(function(v) { return v === null})){
                    y = this.scatter_y.cv;
                    title_y = "cv"
                }
                return {y, title_y};
            },
            errors_x(){
              var x;
              var title_x;
              if  (!this.scatter_x.sd.every(function(v) { return v === null})) {
                x = this.scatter_x.sd;
                title_x = "sd"
              }
              else if (!this.scatter_x.se.every(function(v) { return v === null})){
                x = this.scatter_x.se;
                title_x = "se"
              }
              else if (!this.scatter_x.cv.every(function(v) { return v === null})){
                x = this.scatter_x.cv;
                title_x = "cv"
              }
              return {x, title_x};
            },
            data(){
                return [{
                    x: this.values_x.x,
                    y: this.values_y.y,
                    type: 'scatter',
                    mode: 'markers',
                    error_y: {
                        type: 'data',
                        array: this.errors_y.y,
                        visible: true,
                        color: '#555555',
                    },
                    error_x: {
                      type: 'data',
                      array: this.errors_x.x,
                      visible: true,
                      color: '#555555',
                    },
                    marker: {
                        color: '#000000',
                        size: 8
                    },
                }]
            },
            layout(){
                var xaxis = {
                  title: "[" + this.scatter_x.unit[0]+ "]",
                  titlefont: {
                        size: 10,
                        color: 'black'
                    },
                    showticklabels: true,
                    tickfont: {
                        size: 10,
                        color: 'black'
                    },
                };
                var yaxis = {
                  //title: this.timecourse.substance + " [" + this.timecourse.unit+ "]",
                  title: "[" + this.scatter_y.unit[0]+ "]",

                  titlefont: {
                        size: 10,
                        color: 'black'
                    },
                    showticklabels: true,
                    tickfont: {
                        size: 10,
                        color: 'black'
                    },
                };


                return {
                    xaxis,
                    yaxis,

                    autosize: true,
                    width: 300,
                    height: 200,
                    margin:{ l: 40, r: 0, b: 30, t: 5, pad: 0 }

                };
            },
            options(){
                return {
                    displayModeBar: false
                };
            },
        }

    }
</script>

<style scoped>
</style>