<template>
    <v-card>
        <Heading :title="'Reference: '+reference.pk" :icon="icon('reference')" :resource_url="resource_url"/>

        Sid: <v-icon>{{ icon('reference') }}</v-icon>{{ reference.sid }}<br />
        Pmid: <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+reference.pmid" target="_blank"> {{ reference.pmid }}</a><br />
        Name: {{ reference.name }}<br />
        Title: {{ reference.title }}<br />
        Journal: {{ reference.journal }}<br />
        Date: {{reference.date}}<br />
        Abstract: {{reference.abstract}}<br />
    </v-card>
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

</style>