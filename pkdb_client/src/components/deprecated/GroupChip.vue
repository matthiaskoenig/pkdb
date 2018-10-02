<template>
    <div class="md-layout-item">
    <CharacteristicaDetail v-for="(value,index) in group.characteristica_all_final" :key="index" :api="api" :id="id_from_url(value)" :parent_count="group.count"/>
    </div>
</template>

<script>
    import axios from 'axios'
    import CharacteristicaDetail from './CharacteristicaDetail'
    import {id_from_url} from "../../utils";

    export default {
        name: "GroupChip",
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