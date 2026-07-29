import { Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { DeviceList } from './pages/DeviceManagement';
import { LivePreview } from './pages/LivePreview';
import { Playback } from './pages/Playback';
import { TvWall } from './pages/TvWall';
import { AlarmPlans, AlarmTemplates, AlarmTypes, EventSubscriptions, AlarmBusiness } from './pages/Alarm';
import {
  AlgorithmManagement,
  AlgorithmOrchestration,
  AlgorithmVersions,
  DeploymentTasks,
} from './pages/AlgorithmDeployment';
import {
  ImageDeployPage,
  ImageImageSearch,
  OmniSearchHome,
  TextImageSearch,
  TextVideoSearch,
  TrajectoryPage,
  VideoAnalysisPage,
} from './pages/OmniSearch';
import {
  OmniReviewHome,
  ReviewTaskCreatePage,
  ReviewTasksPage,
  ReviewTypeCreatePage,
  ReviewTypesPage,
  VisualEventActionsPage,
  VisualEventListPage,
  VisualEventStatisticsPage,
} from './pages/OmniReview';
import {
  AlarmSourceCreatePage,
  BasicConfigHome,
  BasicEventConfigHome,
  BasicVideoConfigPage,
  DedupCreatePage,
  DedupLogsPage,
  EventDedupPage,
  EventInfoCreatePage,
  EventInfoPage,
  EventIngestionPage,
  LargeModelDrawerPage,
  LargeModelPage,
  LargeModelResourcesPage,
  PushLogsPage,
  PushTaskFormPage,
  SubscriptionsPage,
} from './pages/BasicConfig';

const blankRoutes = [
  '/omni-review/algo-deploy',
  '/omni-review/algo-deploy/algorithms/create',
  '/omni-review/algo-deploy/algorithms/versions/create',
  '/omni-review/algo-deploy/algorithms/versions/detail',
  '/omni-review/algo-deploy/algorithms/versions/detail/preview',
  '/omni-review/algo-deploy/tasks/create',
  '/algo-deploy/versions/create',
  '/algo-deploy/versions/detail',
  '/algo-deploy/versions/detail/preview',
  '/algo-deploy/algorithms/create',
  '/algo-deploy/tasks/create',
  '/system-modules',
  '/system-modules/permissions',
  '/system-modules/users',
  '/system-modules/logs',
];

function BlankPage() {
  return <div className="blank-page" />;
}

function SxinAssistantPage() {
  return (
    <div className="sxin-assistant-page">
      <iframe
        src="http://10.10.3.100:81/iot-os/sxin/#/mockLogin"
        title="SXin助手"
        allow="fullscreen; clipboard-read; clipboard-write"
      />
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sxin-assistant" element={<SxinAssistantPage />} />
        <Route path="/devices" element={<DeviceList />} />
        <Route path="/live" element={<LivePreview />} />
        <Route path="/playback" element={<Playback />} />
        <Route path="/tvwall" element={<TvWall />} />
        <Route path="/alarm" element={<AlarmPlans />} />
        <Route path="/alarm/templates" element={<AlarmTemplates />} />
        <Route path="/alarm/types" element={<AlarmTypes />} />
        <Route path="/alarm/subscriptions" element={<EventSubscriptions />} />
        <Route path="/alarm/business" element={<AlarmBusiness />} />
        <Route path="/algo-deploy" element={<Navigate to="/algo-deploy/algorithms" replace />} />
        <Route path="/algo-deploy/algorithms" element={<AlgorithmManagement />} />
        <Route path="/algo-deploy/orchestration" element={<AlgorithmOrchestration />} />
        <Route path="/algo-deploy/versions" element={<AlgorithmVersions />} />
        <Route path="/algo-deploy/versions/:algoId" element={<AlgorithmVersions />} />
        <Route path="/algo-deploy/tasks" element={<DeploymentTasks />} />
        <Route path="/omni-search" element={<OmniSearchHome />} />
        <Route path="/omni-search/monitor" element={<TextVideoSearch />} />
        <Route path="/omni-search/text-video" element={<TextVideoSearch />} />
        <Route path="/omni-search/text-video/analysis" element={<VideoAnalysisPage />} />
        <Route path="/omni-search/text-video/analysis/image-search" element={<VideoAnalysisPage />} />
        <Route path="/omni-search/text-video/analysis/append-input" element={<VideoAnalysisPage />} />
        <Route path="/omni-search/text-video/analysis/image-deploy" element={<VideoAnalysisPage />} />
        <Route path="/omni-search/text-video/analysis/trajectory" element={<VideoAnalysisPage />} />
        <Route path="/omni-search/text-image" element={<TextImageSearch />} />
        <Route path="/omni-search/image-image" element={<ImageImageSearch />} />
        <Route path="/omni-search/quick-deploy" element={<ImageDeployPage />} />
        <Route path="/omni-search/quick-deploy/create" element={<ImageDeployPage />} />
        <Route path="/omni-search/trajectory" element={<TrajectoryPage />} />
        <Route path="/omni-search/trajectory/timeline" element={<TrajectoryPage />} />
        <Route path="/omni-search/trajectory/map" element={<TrajectoryPage />} />
        <Route path="/omni-search/exact" element={<TextVideoSearch />} />
        <Route path="/omni-search/tracking" element={<TrajectoryPage />} />
        <Route path="/omni-review" element={<OmniReviewHome />} />
        <Route path="/omni-review/tasks" element={<ReviewTasksPage />} />
        <Route path="/omni-review/tasks/create" element={<ReviewTaskCreatePage />} />
        <Route path="/omni-review/types" element={<ReviewTypesPage />} />
        <Route path="/omni-review/types/create" element={<ReviewTypeCreatePage />} />
        <Route path="/omni-review/visual-events" element={<Navigate to="/omni-review/visual-events/statistics" replace />} />
        <Route path="/omni-review/visual-events/statistics" element={<VisualEventStatisticsPage />} />
        <Route path="/omni-review/visual-events/list" element={<VisualEventListPage />} />
        <Route path="/omni-review/visual-events/list/actions" element={<VisualEventActionsPage />} />
        <Route path="/visual-events" element={<Navigate to="/omni-review/visual-events/statistics" replace />} />
        <Route path="/visual-events/statistics" element={<VisualEventStatisticsPage />} />
        <Route path="/visual-events/list" element={<VisualEventListPage />} />
        <Route path="/visual-events/list/actions" element={<VisualEventActionsPage />} />
        <Route path="/basic-config" element={<BasicConfigHome />} />
        <Route path="/basic-config/video" element={<BasicVideoConfigPage />} />
        <Route path="/basic-config/events" element={<BasicEventConfigHome />} />
        <Route path="/basic-config/events/info" element={<EventInfoPage />} />
        <Route path="/basic-config/events/info/create" element={<EventInfoCreatePage />} />
        <Route path="/basic-config/events/ingestion" element={<EventIngestionPage />} />
        <Route path="/basic-config/events/ingestion/alarm-source" element={<AlarmSourceCreatePage />} />
        <Route path="/basic-config/events/dedup" element={<EventDedupPage />} />
        <Route path="/basic-config/events/dedup/create" element={<DedupCreatePage />} />
        <Route path="/basic-config/events/dedup/logs" element={<DedupLogsPage />} />
        <Route path="/basic-config/events/dedup/logs/detail" element={<DedupLogsPage detail />} />
        <Route path="/basic-config/events/subscriptions" element={<SubscriptionsPage />} />
        <Route path="/basic-config/events/subscriptions/push-logs-latest" element={<PushLogsPage tab="latest" />} />
        <Route path="/basic-config/events/subscriptions/push-logs-history" element={<PushLogsPage tab="history" />} />
        <Route path="/basic-config/events/subscriptions/create-mq" element={<PushTaskFormPage type="mq" />} />
        <Route path="/basic-config/events/subscriptions/create-http" element={<PushTaskFormPage type="http" />} />
        <Route path="/basic-config/large-model" element={<LargeModelPage />} />
        <Route path="/basic-config/large-model/create" element={<LargeModelDrawerPage mode="create" />} />
        <Route path="/basic-config/large-model/edit" element={<LargeModelDrawerPage mode="edit" />} />
        <Route path="/basic-config/large-model/resources" element={<LargeModelResourcesPage />} />
        {blankRoutes.map(path => (
          <Route key={path} path={path} element={<BlankPage />} />
        ))}
      </Route>
    </Routes>
  );
}
