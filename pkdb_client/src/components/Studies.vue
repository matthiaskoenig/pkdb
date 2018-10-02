<template>
        <GetData :resource_url="resource_url" >
            <div slot-scope="resource">
                    <md-table  md-height="800px" class="my-table" v-model="resource.entries" v-if="resource.count" md-card>

                        <md-table-toolbar>
                            <md-badge  class="md-square md-primary" :md-content="resource.count">
                                <h3 class="md-title"  style="flex: 1" >
                                    <font-awesome-icon class="md-icon"  icon="procedures" />
                                    <span class="md-list-item-text">Studies</span>
                                </h3>
                            </md-badge>

                            <md-button :href="resource_url" title="JSON" target="_blank" class="md-icon-button md-raised">
                                <font-awesome-icon icon="code"/>
                            </md-button>
                        </md-table-toolbar>

                        <md-table-row slot="md-table-row" slot-scope="{item}">
                            <md-table-cell  md-label="Pk">
                                <md-button :to="'studies/'+ item.pk" class="md-icon-button md-raised">
                                    <font-awesome-icon icon="procedures"/>
                                </md-button>{{ item.pk }}

                            </md-table-cell>
                            <md-table-cell md-label="Pkdb Version" >{{ item.pkdb_version }}</md-table-cell>
                            <md-table-cell md-label="Name">{{ item.name }}</md-table-cell>
                            <md-table-cell md-label="Reference"><a v-if="item.reference" :href="item.reference" :title="item.reference"><font-awesome-icon icon="file-alt"/> </a></md-table-cell>
                            <md-table-cell md-label="Creator">
                                <md-list>
                                    <md-list-item>
                                         <font-awesome-icon class="md-icon" icon="user-cog"/>
                                    </md-list-item>
                                    <span class="md-list-item-text">{{item.creator.first_name}} {{item.creator.last_name}}</span>
                                </md-list>
                            </md-table-cell>
                            <md-table-cell md-label="Curators"><span v-for="(c, index2) in item.curators" :key="index2"> <font-awesome-icon icon="user-edit"/>{{c.first_name}} {{c.last_name}} </span></md-table-cell>
                            <md-table-cell md-label="Substances"><span v-for="(c, index2) in item.substances" :key="index2"><font-awesome-icon icon="tablets"/> {{c.name}}</span></md-table-cell>
                            <md-table-cell md-label="Files"><span v-for="(f, index2) in item.files" :key="index2"><a :href="f" :title="f"><font-awesome-icon icon="file-medical"/></a>&nbsp;</span> </md-table-cell>
                            <md-table-cell md-label="Groupset"><a v-if="item.groupset" :href="item.groupset" :title="item.groupset"><font-awesome-icon icon="users"/></a></md-table-cell>
                            <md-table-cell md-label="Individualset"><a v-if="item.individualset" :href="item.individualset" :title="item.individualset"><font-awesome-icon icon="user"/></a></md-table-cell>
                            <md-table-cell md-label="Interventionset"><a v-if="item.interventionset" :href="item.interventionset" :title="item.interventionset"><font-awesome-icon icon="capsules"/>
                            </a></md-table-cell>
                            <md-table-cell md-label="Outputset"><a v-if="item.outputset" :href="item.outputset" :title="item.outputset"> <font-awesome-icon icon="chart-bar"/>
                            </a></md-table-cell>
                            <md-table-cell md-label="Design">{{ item.design }}</md-table-cell>
                            <md-table-cell md-label="Keywords"><span v-for="(c, index2) in item.keywords" :key="index2">
                                    <a :href="c" :title="c"><font-awesome-icon icon="tablets"/></a>&nbsp;</span>
                            </md-table-cell>
                        </md-table-row>
                    </md-table>
            </div>
        </GetData>
</template>

<script>
    import Table from '@/components/tables/Table';
    import GetData from '@/components/api/GetPaginatedData';

    export default {
        name: 'Studies',
        components: {
            GetData: GetData,
        },
        computed: {
            api() {return this.$store.state.endpoints.api},
            resource_url() {
                return this.api + '/studies_read/?format=json';
            },
        }
    }
</script>

<style></style>