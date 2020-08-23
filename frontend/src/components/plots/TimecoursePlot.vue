<template>
    <span class="small-timeseries">
        <vue-plotly :data="data" :layout="layout" :options="options"/>
    </span>
</template>

<script>
    import VuePlotly from '@statnett/vue-plotly'

    export default {
        name: "TimecoursePlot",
        props: {
          array: {
                type: Array,
                required: true
            },
        },
      methods:{
        compare( a, b ) {
          if ( a.time < b.time ){
            return -1;
          }
          if ( a.time > b.time ){
            return 1;
          }
          return 0;
        }
      },
        components: {
            VuePlotly,
        },
        computed: {
          timecourse: function(){
            let timecourse = this.array.map(function(point){
              return {
                "time": point[0].time,
                "unit": point[0].unit,
                "time_unit": point[0].time_unit,
                "sd": point[0].sd,
                "se": point[0].se,
                "cv": point[0].cv,
                "mean":point[0].mean,
                "median":point[0].median,
                "value":point[0].value,

              }
            })
            timecourse = timecourse.sort(this.compare)

            var out = {};
            for (var i = 0; i < timecourse.length; i++) {
              for (var key in timecourse[i]) {
                if (out[key] === undefined) {
                  out[key] = [];
                }
                out[key].push(timecourse[i][key]);
              }
            }
            return out
          },
            values(){
                var y;
                var title_y;
                if  (!this.timecourse.value.every(function(v) { return v === null})) {
                    y = this.timecourse.value;
                    title_y = "value"
                }
                else if (!this.timecourse.mean.every(function(v) { return v === null})){
                    y = this.timecourse.mean;
                    title_y = "mean"
                }
                else if (!this.timecourse.median.every(function(v) { return v === null})){
                    y = this.timecourse.median;
                    title_y = "median"
                }
                return {y, title_y};
            },
            errors(){
                var y;
                var title_y;
                if  (!this.timecourse.sd.every(function(v) { return v === null})) {
                    y = this.timecourse.sd;
                    title_y = "sd"
                }
                else if (!this.timecourse.se.every(function(v) { return v === null})){
                    y = this.timecourse.se;
                    title_y = "se"
                }
                else if (!this.timecourse.cv.every(function(v) { return v === null})){
                    y = this.timecourse.cv;
                    title_y = "cv"
                }
                return {y, title_y};
            },
            data(){
                return [{
                    x: this.timecourse.time,
                    y: this.values.y,
                    type: 'scatter',
                    error_y: {
                        type: 'data',
                        array: this.errors.y,
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
                    title: "time [" + this.timecourse.time_unit[0]+ "]",
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
                  title: "[" + this.timecourse.unit[0]+ "]",

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