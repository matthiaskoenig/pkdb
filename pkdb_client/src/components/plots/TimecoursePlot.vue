<template>
    <div class="small-timeseries">
        <vue-plotly :data="data" :layout="layout" :options="options"/>
    </div>
</template>

<script>
    import {clean} from "@/utils"
    import VuePlotly from '@statnett/vue-plotly'

    export default {
        name: "TimecoursePlot",
        props: {
            timecourse: {
                type: Object,
                required: true
            },
        },
        components: {
            VuePlotly,
        },
        computed: {
            values(){
                var y;
                var title_y;
                if  (this.timecourse.value != null && this.timecourse.value !== undefined) {
                    y = this.timecourse.value;
                    title_y = "value"
                }
                else if (this.timecourse.mean != null && this.timecourse.mean !== undefined){
                    y = this.timecourse.mean;
                    title_y = "mean"
                }
                else if (this.timecourse.median != null && this.timecourse.median !== undefined){
                    y = this.timecourse.median;
                    title_y = "median"
                }
                return {y, title_y};
            },
            errors(){
                var y;
                var title_y;
                if  (this.timecourse.sd != null && this.timecourse.sd !== undefined) {
                    y = this.timecourse.sd;
                    title_y = "sd"
                }
                else if (this.timecourse.se != null && this.timecourse.se !== undefined){
                    y = this.timecourse.se;
                    title_y = "se"
                }
                else if (this.timecourse.cv != null && this.timecourse.cv !== undefined){
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
                    title: "time [" + this.timecourse.time_unit+ "]",
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
                    title: this.timecourse.substance.name + " [" + this.timecourse.unit+ "]",
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