<template>

    <div>
        <v-paginator :resource_url="resource_url"  @update="updateResource"></v-paginator>
        <h1>Studies <span v-if="count">({{ count }})</span></h1>
        <table v-if="count">
            <thead>
            <tr>
                <th>sid</th>
                <th>pkdb_version</th>
                <th>name</th>
                <th>reference</th>
                <th>creator</th>
                <th>curators</th>
                <th>substances</th>
                <th>design</th>
                <!--<th>groups</th>
                <th>individuals</th>
                <th>interventions</th>
                <th>outputs</th>
                <th>timecourses</th>-->
                <th>files</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="(study, index) in studies" :key="index">
                <td>{{ study.sid }}</td>
                <td>{{ study.pkdb_version }}</td>
                <td>{{ study.name }}</td>
                <td>{{ study.reference }}</td>
                <td>{{ study.creator }}</td>
                <td>
                    <li v-for="(curator, index) in study.curators" :key="index">
                        {{ curator }}
                    </li>
                </td>
                <td>
                    <li v-for="(substance, index) in study.substances" :key="index">
                        {{ substance }}
                    </li>
                </td>
                <td>{{ study.design }}</td>
                <!--<td>{{ study.groupset.groups.length }}</td>
                <td>{{ study.individualset.individuals.length }}</td>
                <td>{{ study.interventionset.interventions.length }}</td>
                <td>{{ study.outputset.outputs.length }}</td>
                <td>{{ study.outputset.timecourses.length }}</td>-->
                <td>
                    <li v-for="(file, index) in study.files" :key="index">
                        <a :href="file">{{ file }}</a>
                    </li>
                </td>
            </tr>
            </tbody>
        </table>
        <p>
        </p>
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
        methods:{
            updateResource(data){
                this.studies = data.data
                this.count = data.count
            }
        },
        data() {
            return {
                studies: [],
                count: null,
                resource_url: this.api + '/studies/?format=json',
            }
        }
    }
</script>