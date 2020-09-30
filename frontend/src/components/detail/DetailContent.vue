<template>
  <v-card flat class="ma-0 pa-0 parent_color" width="100%" v-if="!mini">
    <v-card-text class="mt-0 pt-0">
        <info-node-detail v-if="show_type === 'info_node'" :data="detail_info"/>
        <search-help v-if="show_type === 'help'"/>
        <study-overview v-if="show_type === 'study'" :study="detail_info"/>
        <subject-detail v-if="show_type === 'individual'" :subject="detail_info"  subject_type="individual"/>
        <subject-detail v-if="show_type === 'group'" :subject="detail_info" subject_type="group"/>
        <intervention-detail v-if="show_type === 'intervention'" :intervention="detail_info"/>
    </v-card-text>
  </v-card>
</template>

<script>
import SearchHelp from "../search/SearchHelp";
import InfoNodeDetail from "../detail/InfoNodeDetail";
import StudyOverview from "../detail/StudyOverview";
import InterventionDetail from "../detail/InterventionDetail";
import {StoreInteractionMixin} from "../../storeInteraction";
import SubjectDetail from "./SubjectDetail";
export default {
  name: "DetailContent",
  components:{SubjectDetail, SearchHelp,InfoNodeDetail, StudyOverview, InterventionDetail},
  mixins: [StoreInteractionMixin],
}
</script>

<style scoped>
.parent_color{
  background-color: inherit;
}
</style>