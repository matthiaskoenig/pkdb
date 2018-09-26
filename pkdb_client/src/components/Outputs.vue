<template>
    <div>
        <md-table  md-height="800px" class="my-table" v-model="entries" v-if="count" md-card>

            <md-table-toolbar>
                <md-badge  class="md-square md-primary" :md-content="count">
                    <h3 class="md-title"  style="flex: 1" ><font-awesome-icon icon="chart-bar" /> Outputs  </h3>
                </md-badge>

                <md-button :href="resource_url" title="JSON" target="_blank" class="md-icon-button md-raised">
                    <font-awesome-icon icon="code"/>
                </md-button>
            </md-table-toolbar>

            <md-table-row slot="md-table-row" slot-scope="{item}">
                <md-table-cell md-label="Pk"> <font-awesome-icon icon="chart-bar" /> {{ item.pk }} </md-table-cell>
                <md-table-cell md-label="PK Type" >{{ item.pktype }}</md-table-cell>
                <md-table-cell md-label="Group" ><a v-if="item.group" :href="item.group" :title="item.group"><font-awesome-icon icon="users" /></a></md-table-cell>
                <md-table-cell md-label="Individual"><a v-if="item.individual" :href="item.individual" :title="item.individual"><font-awesome-icon icon="user" /></a></md-table-cell>
                <md-table-cell md-label="Interventions"><span v-for="(intervention, index2) in item.interventions" :key="index2">
                        <a :href="intervention" :title="intervention"><font-awesome-icon icon="capsules" /></a>&nbsp;</span></md-table-cell>
                <md-table-cell md-label="Tissue">{{item.tissue}}</md-table-cell>
                <md-table-cell md-label="Substance"><a v-if="item.substance" :href="item.substance" :title="item.substance"><font-awesome-icon icon="tablets" /></a></md-table-cell>
                <md-table-cell md-label="Time"> {{item.time}} </md-table-cell>
                <md-table-cell md-label="Time Unit"> {{ item.time_unit }} </md-table-cell>
                <md-table-cell md-label="Unit"> {{item.unit}} </md-table-cell>
                <md-table-cell md-label="Value"> {{ item.value }} </md-table-cell>
                <md-table-cell md-label="Mean"> {{ item.mean }}</md-table-cell>
                <md-table-cell md-label="Median"> {{ item.median }}</md-table-cell>
                <md-table-cell md-label="Min">{{ item.min }}</md-table-cell>
                <md-table-cell md-label="Max">{{ item.max }}</md-table-cell>
                <md-table-cell md-label="Sd">{{ item.sd }}</md-table-cell>
                <md-table-cell md-label="Se">{{ item.se }}</md-table-cell>
                <md-table-cell md-label="Cv">{{ item.cv }}</md-table-cell>

            </md-table-row>
        </md-table>
        <v-paginator :resource_url="resource_url" @update="updateResource"></v-paginator>
    </div>
</template>
<script>

    import VuePaginator from '@/components/VPaginator';
export default {
    name: 'Outputs',
    components: {
        VPaginator: VuePaginator
    },
    props: {
        api: String
    },
    methods:{
        updateResource(data){
            this.entries = data.data;
            this.count = data.count
        }
    },
    data() {
        return {
            entries: [],
            count: null,
            resource_url: this.api + '/outputs_read/?format=json&final=True',
            }
        }
}
</script>
<style>

</style>