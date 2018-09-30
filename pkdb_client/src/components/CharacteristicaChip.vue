<template>
    <div class="small-card">

        <md-card :class="'md-card ' + color">
            <md-ripple>

                <md-badge  v-if="characteristica.group_name" class="md-square md-primary" :md-content="characteristica.group_name" />
                <!-- <md-badge md-dense v-if="characteristica_no_options.count" class="md-square md-primary" :md-content="characteristica_no_options.count" /> -->

                <md-card-content class="md-card-content">
                <div class="md-title">{{characteristica_no_options.choice}}</div>
                <div class="md-subhead title_sub">{{characteristica_no_options.category}}</div>
                <div class="card-reservation">
                    <div v-for="(value, key) in characteristica_clean" :key="key">
                        <div class="values">
                            <span>{{value}} </span>
                            <div class="key">{{key}}</div>
                        </div>


                    </div>
                </div>

            </md-card-content>
            </md-ripple>
        </md-card>

    </div>


</template>

<script>
    import axios from 'axios'
    import {clean} from "./utils"
    export default {
        name: "CharacteristicaChip",

        props: {
            api: String,
            id: String,
            parent_count: Number,
            color: String
        },

        data() {
            return {
                characteristica: {},
                resource_url: this.api + '/characteristica_read/' + this.id + '/?format=json',

            }
        },
        // Fetches posts when the component is created.
        created() {
            axios.get(this.resource_url)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.characteristica = response.data
                })
                .catch(e => {
                    this.errors.push(e)
                })

        },
        computed: {
            characteristica_no_options(){
                delete this.characteristica.options;
                return this.characteristica;
            },
            characteristica_clean(){
                delete this.characteristica_no_options.category;
                delete this.characteristica_no_options.pk;
                delete this.characteristica_no_options.final;
                delete this.characteristica_no_options.choice;
                delete this.characteristica_no_options.ctype;
                delete this.characteristica_no_options.group_name;
                if (this.characteristica_no_options.group_name) {
                    delete this.characteristica_no_options.group_name;
                }

                if (this.parent_count === this.characteristica_no_options.count) {
                    delete this.characteristica_no_options.count
                }


                clean(this.characteristica_no_options);


                return this.characteristica_no_options;
            }

        }

    }


</script>

<style  scoped>



    .key{
        opacity: .54;
        font-size: 14px;
        letter-spacing: .01em;
        line-height: 20px;
    }

    .card-reservation {
        margin-top: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;

    }

    .md-card {
        width: 300px;
        height: 110px;
        margin: 5px;
        display: inline-block;
        vertical-align: top;
        position: relative;


    }
    .md-card-content {
        padding-top: 1px;
        padding-bottom: 1px;
        margin: 1px;
        position: absolute;
        bottom: 0;




    }
    .md-card-content:last-of-type {
        padding-bottom: 0px;
    }
    .values {padding: 2px}





</style>