<template>
    <div id="about">
        <v-layout>
            <v-flex xs6>
                <get-data :resource_url="characteristica_options_url">
                  <template slot-scope="characteristica">
                      <characteristica-browser :options="characteristica.data" title="Characteristica"/>
                  </template>
                </get-data>
            </v-flex>
            <v-flex xs6>
                <get-data :resource_url="intervention_options_url">
                    <template slot-scope="intervention">
                        <characteristica-browser :options="intervention.data" title="Interventions"/>
                    </template>
                </get-data>
            </v-flex>
            <v-flex xs6>
                <get-data :resource_url="output_options_url">
                    <template slot-scope="output">
                        <output-browser :options="output.data" title="PK types"/>
                    </template>
                </get-data>
            </v-flex>
            <v-flex xs6>
                <get-data :resource_url="output_options_url">
                    <template slot-scope="output">
                        <substance-browser :options="output.data" title="Substances"/>
                    </template>
                </get-data>
            </v-flex>


        </v-layout>
    </div>
</template>

<script>
    import CharacteristicaBrowser from "./curation/CharacteristicaBrowser"
    import OutputBrowser from "./curation/OutputBrowser"
    import SubstanceBrowser from "./curation/SubstanceBrowser"

    export default {
        name: "Curation",
        components: {
            CharacteristicaBrowser,
            OutputBrowser,
            SubstanceBrowser
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