<template>
<span>
    <v-tabs
            v-model="active"
            color="#999999"
            dark
            slider-color="yellow">
        <v-tab
                v-for="(item, i) in files"
                :key="i"
                ripple
        >
            {{ id_from_name(item.name) }}

        </v-tab>
        <v-tab-item v-for="item in files" :key="item.name">
            <v-card flat>
                <v-btn flat small><a :href="backend+item.file" target="blank">{{ item.name }}</a></v-btn>
                <get-file :resource_url="backend+item.file">
                    <template slot-scope="data">
                        <v-img :src="data.data"  max-height="500" max-width="500" :alt="item.name" :contain="true" @click="next"> </v-img>
                    </template>
                </get-file>

            </v-card>

            <!-- Timecourse plots
            <v-divider></v-divider>
            <v-card flat>
               <get-data v-if="item.timecourses.length > 0" :resource_url="timecourses_url(item.timecourses)">
                    <span slot-scope="timecourses">
                        <timecourses-plot :timecourses="timecourses.data.data.data"/>
                    </span>
                </get-data>
            </v-card>
            -->
        </v-tab-item>
    </v-tabs>

    </span>
</template>

<script>
    /**
     * Displaying files from the database.
     */
    import {lookup_icon} from "@/icons"
    import {UrlMixin} from "../tables/mixins";
    import GetFile from "../api/GetFile";

    import TimecoursesPlot from "../plots/TimecoursesPlot";

    export default {
        name: "FileImageView",
        components: {TimecoursesPlot,GetFile},
        props: {
            files: {
                type: Array,
                required: true,
            }
        },
        mixins:[UrlMixin],
        data () {
            return {
                active: null,
            }
        },
        computed: {
            backend(){
                    return this.$store.state.django_domain;
                },
            images() {
                var list = [];
                for (var k=0; k<this.files.length; k++){
                    var item = this.files[k];
                    if (item.name.endsWith("png")){
                        list.push(item)
                    }
                }
                return list.sort(function(a, b){
                    return a.name.localeCompare(b.name)
                });

            },
            token(){
            return localStorage.getItem('token')
        }
        },
        methods: {
            file_data: function (data){
                var base64 = require('base-64');
                return base64.encode(data)
            },


            id_from_name: function (name) {
                let tokens = name.split("_");
                let id = tokens[tokens.length-1];
                id = id.split(".")[0];
                return id
            },
            icon: function (key) {
                return lookup_icon(key)
            },
            next () {
                const active = parseInt(this.active);
                this.active = (active < (this.images.length-1) ? active + 1 : 0)
            }
        }
    }
</script>

<style scoped>
    .v-card {
        padding: 10px;
    }
</style>