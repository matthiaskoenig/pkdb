<template>
    <div>
        <div class="md-layout">

            <div class="md-title md-layout-item">Group: {{group.name}}</div>
            <div class="md-layout-item"> Count: {{group.count}} </div>

        </div>

        <div class="md-layout md-gutter md-alignment-center">
            <div class="md-layout-item md-medium-size-33 md-small-size-50 md-xsmall-size-100" v-for="(value,index) in group.characteristica_all_final" :key="index">
            <CharacteristicaDetail :api="api" :id="id_from_url(value)" :parent_count="group.count"/>
        </div>
        </div>

    </div>
</template>

<script>
    import axios from 'axios'
    import CharacteristicaDetail from './CharacteristicaDetail'
    import {id_from_url} from "./utils";

    export default {
        name: "GroupDetail",
        components:{CharacteristicaDetail},
        props: {
            api: String,
            id: String,
        },

        data() {
            return {
                group: {},
                resource_url: this.api + '/groups_read/' + this.id + '/?format=json',
            }
        },
        // Fetches posts when the component is created.
        created() {
            axios.get(this.resource_url)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.group = response.data
                })
                .catch(e => {
                    this.errors.push(e)
                })

        },
        methods:{
            id_from_url(url){
                return id_from_url(url);
            }
        }

    }
</script>

<style scoped>



</style>