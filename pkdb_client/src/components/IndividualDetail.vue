<template>

    <div class="mdc-card">
        <h1>Individual</h1>
        <p> Name: {{individual.name}} </p>
        <p> group: {{individual.group}} </p>

        <div class="md-layout md-gutter">
            <div class="md-layout-item" v-for="(value,index) in individual.characteristica_final" :key="index">
                <CharacteristicaDetail :api="api" :id="id_from_url(value)" />
            </div>
        </div>
    </div>
</template>

<script>
    import axios from 'axios'
    import CharacteristicaDetail from './CharacteristicaDetail'
    import GroupDetail from './GroupDetail'
    import { id_from_url } from './utils';

    export default {
        name: "IndividualDetail",
        components:{CharacteristicaDetail, GroupDetail},
        props: {
            api: String,
            id: String,
        },
        data() {
            return {
                individual: {},
                resource_url: this.api + '/individuals_read/' + this.id + '/?format=json',
            }
        },
        // Fetches posts when the component is created.
        created() {
            axios.get(this.resource_url)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.individual = response.data
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