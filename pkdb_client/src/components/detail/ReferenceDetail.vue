<template>
    <div id="reference-detail">
        <!-- <heading-toolbar :title="reference.name" :icon="icon('reference')" :resource_url="resource_url"/>-->

        <v-toolbar color="secondary" dark>
            <v-layout>
                <v-flex xs1>
                    <v-icon>{{ icon('reference') }}</v-icon>
                </v-flex>
                <v-flex xs11>
                    {{ reference.title }}
                </v-flex>
            </v-layout>
        </v-toolbar>

        <v-card max-width="1000" flat>
            <span v-for="(author, index) in reference.authors" :key="index">
                {{ author.first_name }} {{ author.last_name }},
            </span><br />
            <i>{{ reference.journal }}, {{reference.date}}</i><br/>
            <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+reference.pmid" target="_blank">PMID:{{reference.pmid }}</a><br/>
            <br />
            {{reference.abstract}}<br/>
        </v-card>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"


    export default {
        name: "ReferenceDetail",
        components: {},
        props: {
            reference: {
                type: Object,
            },
            resource_url: {
                type: String
            }
        },
        computed: {
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>
.v-card{
    padding: 10px;
}
</style>