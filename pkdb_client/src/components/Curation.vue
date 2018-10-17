<template>
    <div id="about">
        <v-layout>
            <v-flex xs6>
                <h1>Characteristica</h1>
                <get-data :resource_url="characteristica_options_url">
                  <template slot-scope="characteristica">
                      <characteristica-browser :options="characteristica.data" />
                  </template>
                </get-data>
            </v-flex>
            <v-flex xs6>
                <h1>Interventions</h1>
                <get-data :resource_url="intervention_options_url">
                    <template slot-scope="intervention">
                        <characteristica-browser :options="intervention.data" />
                    </template>
                </get-data>
            </v-flex>
            <v-flex xs6>
                <h1>Outputs</h1>
                <get-data :resource_url="output_options_url">
                    <template slot-scope="output">
                        <output-browser :options="output.data" />
                    </template>
                </get-data>
            </v-flex>

        </v-layout>
    </div>
</template>

<script>
    import CharacteristicaBrowser from "./curation/CharacteristicaBrowser"
    import OutputBrowser from "./curation/OutputBrowser"

    export default {
        name: "Curation",
        components: {
            CharacteristicaBrowser,
            OutputBrowser
        },
        computed: {
            characteristica_options_url() {
                return this.$store.state.endpoints.api + '/characteristica_options/';
            },
            intervention_options_url() {
                return this.$store.state.endpoints.api + '/intervention_options/';
            },
            output_options_url() {
                return this.$store.state.endpoints.api + '/output_options/';
            },

        }
    }
</script>

<style scoped>

</style>