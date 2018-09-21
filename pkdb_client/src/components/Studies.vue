<template>
    <div>
    <h1><font-awesome-icon icon="procedures"/>Studies <span v-if="count">({{ count }})</span></h1>
    <a :href="resource_url" title="JSON" target="_blank">
        <font-awesome-icon icon="code"/>
    </a>

        <v-paginator :resource_url="resource_url" @update="updateResource"></v-paginator>

        <md-table v-if="count" md-card>
            <thead>
            <md-table-row>
                <md-table-head>pk</md-table-head>
                <md-table-head>pkdb_version</md-table-head>
                <md-table-head>name</md-table-head>
                <md-table-head>reference</md-table-head>
                <md-table-head>creator</md-table-head>
                <md-table-head>curators</md-table-head>
                <md-table-head>substances</md-table-head>
                <md-table-head>files</md-table-head>
                <md-table-head>groupset</md-table-head>
                <md-table-head>individualset</md-table-head>
                <md-table-head>interventionset</md-table-head>
                <md-table-head>outputset</md-table-head>
                <md-table-head>timecourseset</md-table-head>
                <md-table-head>design</md-table-head>
                <md-table-head>keywords</md-table-head>
            </md-table-row>
            </thead>
            <tbody>
            <md-table-row v-for="(entry, index) in entries" :key="index">
                <md-table-cell>
                    <font-awesome-icon icon="procedures"/>
                    {{ entry.pk }}
                </md-table-cell>
                <md-table-cell>{{ entry.pkdb_version }}</md-table-cell>
                <md-table-cell>{{ entry.name }}</md-table-cell>
                <md-table-cell><a v-if="entry.reference" :href="entry.reference" :title="entry.reference">
                    <font-awesome-icon icon="file-alt"/>
                </a></md-table-cell>
                <md-table-cell><a v-if="entry.creator" :href="entry.creator" :title="entry.creator">
                    <font-awesome-icon icon="user-cog"/>
                </a></md-table-cell>
                <md-table-cell><span v-for="(c, index2) in entry.curators" :key="index2">
                        <a :href="c" :title="c"><font-awesome-icon icon="user-edit"/></a>&nbsp;</span>
                </md-table-cell>
                <md-table-cell><span v-for="(c, index2) in entry.substances" :key="index2">
                        <a :href="c" :title="c"><font-awesome-icon icon="tablets"/></a>&nbsp;</span>
                </md-table-cell>
                <md-table-cell><span v-for="(f, index2) in entry.files" :key="index2">
                        <a :href="f" :title="f"><font-awesome-icon icon="file-medical"/></a>&nbsp;</span>
                </md-table-cell>
                <md-table-cell><a v-if="entry.groupset" :href="entry.groupset" :title="entry.groupset">
                    <font-awesome-icon icon="users"/>
                </a></md-table-cell>
                <md-table-cell><a v-if="entry.individualset" :href="entry.individualset" :title="entry.individualset">
                    <font-awesome-icon icon="user"/>
                </a></md-table-cell>
                <md-table-cell><a v-if="entry.interventionset" :href="entry.interventionset" :title="entry.interventionset">
                    <font-awesome-icon icon="capsules"/>
                </a></md-table-cell>
                <md-table-cell><a v-if="entry.outputset" :href="entry.outputset" :title="entry.outputset">
                    <font-awesome-icon icon="chart-bar"/>
                </a></md-table-cell>
                <md-table-cell><a v-if="entry.timecourseset" :href="entry.timecourseset" :title="entry.timecourseset">
                    <font-awesome-icon icon="chart-bar"/>
                </a></md-table-cell>
                <md-table-cell>{{ entry.design }}</md-table-cell>
                <md-table-cell><span v-for="(c, index2) in entry.keywords" :key="index2">
                        <a :href="c" :title="c"><font-awesome-icon icon="tablets"/></a>&nbsp;</span>
                </md-table-cell>
            </md-table-row>
            </tbody>
        </md-table>
    </div>
</template>

<script>
    import VuePaginator from 'vuejs-paginator';

    export default {
        name: 'Studies',
        components: {
            VPaginator: VuePaginator
        },
        props: {
            api: String
        },
        methods: {
            updateResource(data) {
                this.entries = data.data;
                this.count = data.count
            }
        },
        data() {
            return {
                // The resource variable
                entries: [],
                // Here you define the url of your paginated API
                resource_url: this.api + '/studies_read/?format=json',
                count: null,
            }
        }
    }
</script>

<style></style>