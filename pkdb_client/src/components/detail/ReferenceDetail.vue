<template>
    <div id="reference-detail">
        <!-- <heading-toolbar :title="reference.name" :icon="icon('reference')" :resource_url="resource_url"/>-->
        <v-card max-width="1000">
            <v-icon>{{ icon('reference') }}</v-icon>&nbsp;<b>{{ reference.title }}</b><br/>
            <span v-for="author in reference.authors">
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