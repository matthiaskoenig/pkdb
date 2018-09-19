<template>
    <div>
        <h1>Characteristica</h1>
        <div v-for="(value, key) in characteristica_no_options">
            {{key}}:{{value}}
        </div>
    </div>


</template>

<script>
    import axios from 'axios'

    export default {
        name: "CharacteristicaDetail",

        props: {
            api: String,
            id: String,
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
                return this.characteristica
            }

        }

    }


</script>

<style scoped>

</style>