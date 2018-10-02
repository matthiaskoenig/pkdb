<template>
    <div>
        <md-table md-height="800px" class="my-table" v-model="references" v-if="count" md-card>

            <md-table-toolbar>
                <md-badge class="md-square md-primary" :md-content="count">
                    <h3 class="md-title" style="flex: 1">
                        <font-awesome-icon icon="file-alt"/>
                        References
                    </h3>
                </md-badge>

                <md-button :href="resource_url" title="JSON" target="_blank" class="md-icon-button md-raised">
                    <font-awesome-icon icon="code"/>
                </md-button>
            </md-table-toolbar>

            <md-table-row slot="md-table-row" slot-scope="{item}">
                <md-table-cell md-label="Sid">
                    <font-awesome-icon icon="file-alt"/>
                    {{ item.sid }}
                </md-table-cell>
                <md-table-cell md-label="Pmid"><a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+item.pmid"
                                                  target="_blank">{{ item.pmid }}</a></md-table-cell>
                <md-table-cell md-label="Name">{{ item.name }}</md-table-cell>
                <md-table-cell md-label="Title">{{ item.title }}</md-table-cell>
                <md-table-cell md-label="Journal">{{ item.journal }}</md-table-cell>
                <md-table-cell md-label="Date">{{item.date}}</md-table-cell>
                <md-table-cell md-label="Abstract">{{item.abstract}}</md-table-cell>
            </md-table-row>
        </md-table>
        <v-paginator :resource_url="resource_url" @update="updateResource"></v-paginator>
    </div>
</template>

<script>
    import Table from '@/components/tables/Table'
    import VuePaginator from '@/components/api/VPaginator';

    export default {
        name: 'References',
        components: {
            VPaginator: VuePaginator
        },
        props: {
            api: String
        },
        methods: {
            updateResource(data) {
                this.references = data.data;
                this.count = data.count;
            }
        },
        data() {
            return {
                references: [],
                count: null,
                resource_url: this.api + '/references/?format=json',
            }
        }
    }
</script>
<style>

</style>