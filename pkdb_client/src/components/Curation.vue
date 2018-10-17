<template>
    <div id="about">
        <v-layout>
            <v-flex xs6>
                <h1>Characteristica</h1>
                <get-data :resource_url="characteristica_options_url">
                  <template slot-scope="characteristica">
                      <options-browser :options="characteristica.data" />
                  </template>
                </get-data>
            </v-flex>
            <v-flex xs6>
                <h1>Interventions</h1>
                <get-data :resource_url="intervention_options_url">
                    <template slot-scope="intervention">
                        <options-browser :options="intervention.data" />
                    </template>
                </get-data>
            </v-flex>
        </v-layout>
    </div>
</template>

<script>
    import OptionsBrowser from "./detail/OptionsBrowser"

    export default {
        name: "Curation",
        components: {
            OptionsBrowser
        },
        computed: {
            characteristica_options_url() {
                return this.$store.state.endpoints.api + '/characteristica_options/';
            },
            intervention_options_url() {
                return this.$store.state.endpoints.api + '/intervention_options/';
            },
        }
    }
</script>

<style scoped>

</style>