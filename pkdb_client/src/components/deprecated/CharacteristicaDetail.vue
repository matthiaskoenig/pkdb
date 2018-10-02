<template>
    <div>
        <md-card class="md-card">
            <md-card-header>
                <md-card-header-text class="md-card-header-text" >
                    <div class="md-title">{{characteristica_no_options.choice}}</div>
                    <div class="md-subhead title_sub">{{characteristica_no_options.category}}</div>
                </md-card-header-text>

                <md-card-media>
                    <md-icon  v-if="characteristica_no_options.ctype === 'group'" title="Group Criteria"> group </md-icon>
                    <md-icon  v-if="characteristica_no_options.ctype === 'inclusion'" title="Inclusion Criteria"> add-circle </md-icon>
                    <md-icon  v-if="characteristica_no_options.ctype === 'exclusion'" title="Exclution Criteria"> remove_circle </md-icon>
                </md-card-media>
            </md-card-header>

            <md-card-content>
                <div class="card-reservation">
                    <div v-for="(value, key) in characteristica_clean">
                        <span>{{value}} </span>
                        <div>{{key}}</div>

                    </div>
                </div>

            </md-card-content>

        </md-card>

    </div>
</template>

<script>
    import axios from 'axios'
    import {clean} from "@/utils"
    export default {
        name: "CharacteristicaDetail",
        props: {
            api: String,
            id: String,
            parent_count: Number,
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
                if (this.parent_count === this.characteristica_no_options.count ) {
                    delete this.characteristica_no_options.count
                }

                clean(this.characteristica_no_options);

                return this.characteristica_no_options;
            }
        }
    }
</script>

<style  scoped>
    .md-card {
        width: 320px;
        margin: 4px;
        display: table-cell;
        vertical-align: top;
        align-items: stretch;
    }
    .card-reservation {
        margin-top: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;

    }
    .md-title{
        text-align: left;
    }
    .title_sub{
        text-align: left;
        align-self: flex-end;


    }

</style>